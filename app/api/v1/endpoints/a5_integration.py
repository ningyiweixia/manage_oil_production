"""A5 系统集成与互操作 API。

包含：
- POST /a5/callback: 接收 A5 系统回调（免鉴权）
- POST /a5/sso-token: 生成 SSO 跳转令牌
- GET /a5/sync/status: 查看同步状态
- POST /a5/sync/trigger: 手动触发数据同步
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.redis import cache_client
from app.core.status_codes import A5_LINK_FAILED, BAD_REQUEST
from app.db.session import get_db
from app.models.rbac import User
from app.models.workover import OperationStatus, WorkoverOperationSheet
from app.schemas.a5_integration import (
    A5CallbackPayload,
    A5SyncStatusOut,
    A5SyncTriggerOut,
    A5TokenResponse,
)
from app.schemas.response import ApiResponse, success
from app.services.a5_auth_service import generate_sso_token, verify_a5_callback_signature
from app.services.a5_sync_service import A5_SYNC_COUNT_PREFIX, A5_SYNC_STATUS_KEY, full_sync
from app.tasks.a5_tasks import sync_a5_data_task, sync_anomaly_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/a5", tags=["A5系统集成"])


@router.post("/callback", response_model=ApiResponse[dict])
async def a5_callback(
    payload: A5CallbackPayload,
    request: Request,
    x_a5_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """接收 A5 系统回调的工单状态变更。

    方案要求：
    - A5 工单状态变更后，通过 RESTful 接口主动回调本系统
    - 本系统接收后自动完成数据解析、校验与更新
    - 实时同步刷新修井运行表及对应作业队伍状态

    此接口加入 AUTH_WHITELIST_PATHS 免鉴权，由签名验证安全。
    """
    # 验证回调签名（传递请求体用于 HMAC 校验）
    headers = dict(request.headers)
    body = await request.body()
    body_str = body.decode("utf-8") if body else ""
    if not verify_a5_callback_signature(headers, body_str):
        raise BusinessException(BAD_REQUEST, "A5 回调签名验证失败")

    # 查找对应工单
    sheet = db.query(WorkoverOperationSheet).filter(
        WorkoverOperationSheet.operation_no == payload.operation_no
    ).first()

    if sheet is None:
        logger.warning(f"A5 回调: 工单 {payload.operation_no} 不存在")
        return success({"matched": False, "operation_no": payload.operation_no}, msg="工单未匹配")

    # 更新状态
    old_status = sheet.status
    status_map = {
        "通过": OperationStatus.FINISHED,
        "办结": OperationStatus.FINISHED,
        "驳回": OperationStatus.WAITING_DISPATCH,
        "关闭": OperationStatus.CANCELED,
    }
    new_status = status_map.get(payload.status)
    if new_status:
        sheet.status = new_status
        if new_status == OperationStatus.FINISHED:
            sheet.actual_end_at = datetime.now(timezone.utc)

    sheet.remark = payload.remark
    db.commit()
    db.refresh(sheet)

    logger.info(f"A5 回调成功: {payload.operation_no} {old_status} -> {new_status}")
    return success({
        "matched": True,
        "operation_no": payload.operation_no,
        "old_status": old_status.value if old_status else None,
        "new_status": new_status.value if new_status else None,
    }, msg="回调处理成功")


@router.post("/sso-token", response_model=ApiResponse[A5TokenResponse])
def generate_token(
    well_no: str,
    redirect_path: str = "/workorder",
    _: User = Depends(require_permission("a5:sso")),
) -> ApiResponse[A5TokenResponse]:
    """生成 SSO 跳转令牌，用于前端无缝跳转 A5 系统。"""
    if not well_no:
        raise BusinessException(BAD_REQUEST, "井号不能为空")
    token = generate_sso_token(well_no, redirect_path)
    return success(token)


@router.get("/sync/status", response_model=ApiResponse[A5SyncStatusOut])
def sync_status(
    _: User = Depends(require_permission("a5:read")),
) -> ApiResponse[A5SyncStatusOut]:
    """查看最近一次 A5 数据同步状态。"""
    cached = cache_client.get_json(A5_SYNC_STATUS_KEY) or {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sync_count_today = cache_client.get_json(f"{A5_SYNC_COUNT_PREFIX}{today}") or cached.get("sync_count_today", 0)
    return success(A5SyncStatusOut(
        last_sync_time=cached.get("last_sync_time"),
        last_sync_status=cached.get("last_sync_status", "unknown"),
        last_sync_message=cached.get("last_sync_message", ""),
        sync_count_today=int(sync_count_today or 0),
        is_running=bool(cached.get("is_running", False)),
    ))


@router.post("/sync/trigger", response_model=ApiResponse[A5SyncTriggerOut])
async def trigger_sync(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("a5:sync")),
) -> ApiResponse[A5SyncTriggerOut]:
    """手动触发一次 A5 全量数据同步。"""
    if settings.environment == "local" and not settings.redis_url:
        task_id = f"local-{uuid.uuid4().hex[:12]}"
        await full_sync(db)
        return success(A5SyncTriggerOut(
            task_id=task_id,
            message="本地同步已执行",
        ), msg="同步已执行")

    task = sync_a5_data_task.delay()
    return success(A5SyncTriggerOut(
        task_id=task.id,
        message="A5 数据同步任务已提交",
    ), msg="同步已触发")
