"""工程设计文档生成服务。

核心流程：
1. 获取项目信息（well_no, measures_jsonb）
2. 调用防偏磨系统获取偏磨参数
3. 规则引擎校验（校验不通过阻断生成）
4. 自动生成版本号
5. 模板渲染（python-docx / openpyxl）
6. MinIO 归档
7. 写审计日志
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST
from app.crud.workover_project_pool import get_project_pool
from app.models.approval import ApprovalAction
from app.models.engineering import EngineeringDesignDoc
from app.schemas.engineering import (
    EngineeringDesignCreate,
    EngineeringDesignOut,
    EngineeringDesignQuery,
    RuleCheckResult,
)
from app.services.audit_service import write_approval_log
from app.services.design_rule_engine import validate_design_before_generation
from app.services.fpm_client import FpmClient
from app.services.template_renderer import TemplateRenderer

logger = logging.getLogger(__name__)

BUSINESS_TYPE = "engineering_design_doc"


def _design_snapshot(doc: EngineeringDesignDoc) -> dict[str, Any]:
    return {
        "id": doc.id,
        "project_id": doc.project_id,
        "well_no": doc.well_no,
        "version": doc.version,
        "minio_bucket": doc.minio_bucket,
        "minio_object_key": doc.minio_object_key,
        "checksum": doc.checksum,
        "remark": doc.remark,
    }


def _generate_next_version(db: Session, well_no: str) -> str:
    """自动生成版本号（v1, v2, v3...）。"""
    latest = db.scalar(
        select(EngineeringDesignDoc.version)
        .where(EngineeringDesignDoc.well_no == well_no)
        .order_by(desc(EngineeringDesignDoc.id))
        .limit(1)
    )
    if latest is None:
        return "v1"
    v_str = latest.lstrip("v")
    if v_str.isdigit():
        return f"v{int(v_str) + 1}"
    return "v1"


async def generate_design_document(
    db: Session,
    payload: EngineeringDesignCreate,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> tuple[EngineeringDesignDoc, RuleCheckResult]:
    """生成工程设计文档。

    Args:
        db: 数据库会话
        payload: 创建参数（project_id, well_no, template_type）
        operator_id: 操作人 ID
        operator_ip: 操作人 IP

    Returns:
        (EngineeringDesignDoc, RuleCheckResult) 元组

    Raises:
        BusinessException: 规则校验不通过时阻断生成
    """
    # 1. 获取项目信息
    project = get_project_pool(db, payload.project_id)
    well_no = payload.well_no
    measures = project.measures_jsonb or {}

    # 2. 调用防偏磨系统获取参数
    fpm_client = FpmClient()
    try:
        fpm_params = await fpm_client.fetch_parameters(well_no)
    except BusinessException as exc:
        logger.warning(f"防偏磨参数获取失败: {exc.msg}")
        fpm_params = {}

    # 3. 规则引擎综合校验
    rule_result = validate_design_before_generation(well_no, measures, fpm_params)
    if not rule_result.passed:
        error_detail = "; ".join(rule_result.errors)
        logger.warning(f"工程设计校验不通过: {well_no} -> {error_detail}")
        raise BusinessException(BAD_REQUEST, f"设计校验未通过，已阻断生成: {error_detail}")

    # 4. 生成版本号
    version = _generate_next_version(db, well_no)

    # 5. 模板渲染
    renderer = TemplateRenderer()
    measures_list = measures.get("measures", []) if isinstance(measures, dict) else []
    well_data = {
        "well_no": project.well_no,
        "well_name": project.well_name,
        "block_name": project.block_name,
        "layer": project.layer,
        "report_unit": project.report_unit,
        "production_priority": project.production_priority,
        "reason": project.reason,
        "created_at": str(project.created_at) if project.created_at else "",
    }

    if payload.template_type == "excel":
        doc_content = renderer.render_excel_report(
            operation_data=[{"well_no": well_no, **well_data}]
        )
    else:
        doc_content = renderer.render_word_document(well_data, measures_list)

    # 6. MinIO 归档
    bucket, object_key, checksum = renderer.save_to_minio(doc_content, well_no, version)

    # 7. 创建数据库记录
    design = EngineeringDesignDoc(
        project_id=payload.project_id,
        well_no=well_no,
        version=version,
        minio_bucket=bucket,
        minio_object_key=object_key,
        checksum=checksum,
    )
    db.add(design)
    db.flush()

    # 8. 写审计日志
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE,
        business_id=design.id,
        node_code="DESIGN_GENERATE",
        action=ApprovalAction.CREATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        after_snapshot=_design_snapshot(design),
    )
    db.commit()
    db.refresh(design)

    logger.info(f"工程设计文档生成成功: {well_no} {version}")
    return design, rule_result


def list_design_docs(db: Session, query: EngineeringDesignQuery) -> tuple[list[EngineeringDesignDoc], int]:
    """分页查询工程设计文档列表。"""
    stmt = select(EngineeringDesignDoc)
    if query.well_no:
        stmt = stmt.where(EngineeringDesignDoc.well_no.ilike(f"%{query.well_no}%"))
    if query.project_id:
        stmt = stmt.where(EngineeringDesignDoc.project_id == query.project_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(desc(EngineeringDesignDoc.created_at))
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return list(rows), total


def get_design_doc(db: Session, design_id: int) -> EngineeringDesignDoc:
    """获取设计文档详情。"""
    obj = db.get(EngineeringDesignDoc, design_id)
    if obj is None:
        raise BusinessException(BAD_REQUEST, "工程设计文档不存在")
    return obj


def get_download_url(db: Session, design_id: int, expire_seconds: int = 3600) -> str:
    """生成 MinIO 临时下载链接。"""
    design = get_design_doc(db, design_id)
    renderer = TemplateRenderer()
    return renderer.minio.get_presigned_url(
        design.minio_bucket, design.minio_object_key, expire_seconds
    )


def delete_design_doc(
    db: Session,
    design_id: int,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> None:
    """删除设计文档（物理删除 + 审计日志）。"""
    design = get_design_doc(db, design_id)
    before = _design_snapshot(design)
    db.delete(design)
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE,
        business_id=design.id,
        node_code="DESIGN_DELETE",
        action=ApprovalAction.DELETE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        before_snapshot=before,
    )
    db.commit()
