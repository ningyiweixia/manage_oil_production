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
from app.core.status_codes import BAD_REQUEST
from app.db.session import get_db
from app.models.rbac import User
from app.models.workover import WorkoverOperationSheet
from app.schemas.a5_integration import (
    A5AnalyticsOut,
    A5AnalyticsQuery,
    A5AnalyticsReportOut,
    A5CallbackPayload,
    A5SyncStatusOut,
    A5SyncTriggerOut,
    A5TokenResponse,
)
from app.schemas.response import ApiResponse, success
from app.services.a5_auth_service import generate_sso_token, verify_a5_callback_signature
from app.services.a5_sync_service import (
    A5_SYNC_COUNT_PREFIX,
    A5_SYNC_STATUS_KEY,
    apply_a5_update_to_operation_sheet,
    build_a5_analytics,
    export_a5_analytics_report,
    full_sync,
    process_a5_callback_event,
)
from app.tasks.a5_tasks import sync_a5_data_task

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

    event_id = headers.get("x-a5-event-id")
    result = process_a5_callback_event(
        db,
        payload.model_dump(mode="json"),
        event_id=event_id,
    )

    logger.info("A5 回调事件处理完成: operation_no=%s event_id=%s", payload.operation_no, result.event.event_key)
    return success({
        "matched": result.matched,
        "duplicate": result.duplicate,
        "operation_no": payload.operation_no,
        "event_status": result.event.status.value,
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


@router.get("/analytics/summary", response_model=ApiResponse[A5AnalyticsOut])
def analytics_summary(
    query: A5AnalyticsQuery = Depends(),
    _: User = Depends(require_permission("a5:read")),
) -> ApiResponse[A5AnalyticsOut]:
    """按时间和类别统计 A5 异常情况、特殊工序等关键信息。"""
    return success(build_a5_analytics(query))


@router.get("/analytics/report", response_model=ApiResponse[A5AnalyticsReportOut])
def analytics_report(
    query: A5AnalyticsQuery = Depends(),
    template_name: str | None = None,
    _: User = Depends(require_permission("a5:read")),
) -> ApiResponse[A5AnalyticsReportOut]:
    """按当前统计条件生成 A5 关键情况 Excel 报告。"""
    return success(export_a5_analytics_report(query, template_name=template_name), msg="报告已生成")


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
