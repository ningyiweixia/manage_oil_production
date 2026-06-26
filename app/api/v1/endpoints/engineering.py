"""工程设计管理 API。

包含文档生成、列表查询、下载、删除和规则校验。
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST
from app.crud.workover_project_pool import get_project_pool
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.engineering import (
    DesignGenerateOut,
    EngineeringDesignCreate,
    EngineeringDesignOut,
    EngineeringDesignQuery,
    EngineeringDesignUpdate,
    RuleCheckResult,
)
from app.schemas.pagination import PageResult
from app.schemas.response import ApiResponse, success
from app.services.design_rule_engine import validate_design_before_generation
from app.services.engineering_design_service import (
    delete_design_doc,
    generate_design_document,
    get_design_doc,
    get_download_url,
    list_design_docs,
)
from app.services.fpm_client import FpmClient

router = APIRouter(prefix="/engineering-designs", tags=["工程设计管理"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/", response_model=ApiResponse[PageResult[EngineeringDesignOut]])
def list_items(
    query: EngineeringDesignQuery = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("engineering:read")),
) -> ApiResponse[PageResult[EngineeringDesignOut]]:
    rows, total = list_design_docs(db, query)
    items = [EngineeringDesignOut.model_validate(row) for row in rows]
    return success(
        PageResult(items=items, total=total, page=query.page, page_size=query.page_size)
    )


@router.post("/generate", response_model=ApiResponse[DesignGenerateOut])
async def generate(
    payload: EngineeringDesignCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("engineering:generate")),
) -> ApiResponse[DesignGenerateOut]:
    """一键生成工程设计文档。

    流程：获取项目信息 → 调防偏磨系统 → 规则校验 → 版本号 → 模板渲染 → MinIO 归档
    规则校验不通过时阻断生成并返回错误信息。
    """
    design, rule_result = await generate_design_document(
        db,
        payload,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
    )
    return success(
        DesignGenerateOut(
            design=EngineeringDesignOut.model_validate(design),
            rule_check=rule_result,
        ),
        msg="工程设计文档生成成功",
    )


@router.post("/check-rules", response_model=ApiResponse[RuleCheckResult])
async def check_rules(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("engineering:read")),
) -> ApiResponse[RuleCheckResult]:
    """手动触发现场规则校验（不生成文档）。"""
    project = get_project_pool(db, project_id)
    measures = project.measures_jsonb or {}

    fpm_client = FpmClient()
    fpm_params = await fpm_client.fetch_parameters(project.well_no)

    result = validate_design_before_generation(project.well_no, measures, fpm_params)
    return success(result)


@router.get("/{design_id}", response_model=ApiResponse[EngineeringDesignOut])
def detail(
    design_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("engineering:read")),
) -> ApiResponse[EngineeringDesignOut]:
    return success(EngineeringDesignOut.model_validate(get_design_doc(db, design_id)))


@router.get("/{design_id}/download", response_model=ApiResponse[dict])
def download(
    design_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("engineering:read")),
) -> ApiResponse[dict]:
    """获取设计文档的 MinIO 临时下载链接。"""
    url = get_download_url(db, design_id)
    return success({"download_url": url, "expire_seconds": 3600})


@router.delete("/{design_id}", response_model=ApiResponse[None])
def delete(
    design_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("engineering:delete")),
) -> ApiResponse[None]:
    delete_design_doc(
        db, design_id, operator_id=current_user.id, operator_ip=_client_ip(request)
    )
    return success(msg="已删除")
