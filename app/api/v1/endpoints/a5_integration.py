"""A5 系统集成与互操作 API。

包含：
- POST /a5/callback: 接收 A5 系统回调（免鉴权）
- POST /a5/sso-token: 生成 SSO 跳转令牌
- GET /a5/sync/status: 查看同步状态
- POST /a5/sync/trigger: 手动触发数据同步
"""

import logging
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.api.deps import require_permission
from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.redis import cache_client
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.db.session import get_db
from app.models.rbac import User
from app.services.data_scope_service import apply_workover_operation_scope
from app.schemas.a5_integration import (
    A5AnalyticsOut,
    A5AnalyticsQuery,
    A5AnalyticsReportOut,
    A5CallbackPayload,
    A5MockMeasureReviewOut,
    A5MockReviewDecisionOut,
    A5MockReviewDecisionPayload,
    A5SyncStatusOut,
    A5SyncBatchOut,
    A5SyncTriggerOut,
    A5TokenResponse,
)
from app.schemas.response import ApiResponse, success
from app.services.a5_auth_service import (
    ensure_local_a5_mock_enabled,
    generate_sso_token,
    verify_a5_callback_signature,
    verify_a5_sso_token,
)
from app.services.a5_sync_service import (
    apply_a5_update_by_operation_no,
    A5_SYNC_COUNT_PREFIX,
    A5_SYNC_STATUS_KEY,
    build_a5_analytics,
    export_a5_analytics_report,
    full_sync,
    is_supported_a5_status,
)
from app.tasks.a5_tasks import sync_a5_data_task
from app.models.workover import A5DailyReportRecord, A5SyncBatch, WorkoverOperationSheet

logger = logging.getLogger(__name__)
BUSINESS_TZ = ZoneInfo("Asia/Shanghai")

router = APIRouter(prefix="/a5", tags=["A5系统集成"])


def _get_mock_review_sheet(
    db: Session,
    *,
    operation_no: str,
    token: str,
    current_user: User,
) -> WorkoverOperationSheet:
    ensure_local_a5_mock_enabled()
    sheet_stmt = (
        select(WorkoverOperationSheet)
        .join(WorkoverOperationSheet.project)
        .options(
            selectinload(WorkoverOperationSheet.project),
            selectinload(WorkoverOperationSheet.contractor_capacity),
        )
        .where(WorkoverOperationSheet.operation_no == operation_no)
    )
    sheet = db.scalar(apply_workover_operation_scope(sheet_stmt, current_user))
    if sheet is None:
        raise BusinessException(BAD_REQUEST, "A5模拟工单不存在或无权访问")
    well_no = sheet.project.well_no if sheet.project is not None else operation_no
    verify_a5_sso_token(token, expected_well_no=well_no)
    return sheet


@router.get("/mock/measure-review", response_model=ApiResponse[A5MockMeasureReviewOut])
def get_mock_measure_review(
    token: str,
    operation_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("a5:sso")),
) -> ApiResponse[A5MockMeasureReviewOut]:
    """Read a local-only A5 measure review screen using the issued SSO token."""
    sheet = _get_mock_review_sheet(db, operation_no=operation_no, token=token, current_user=current_user)
    project = sheet.project
    contractor = sheet.contractor_capacity
    return success(A5MockMeasureReviewOut(
        operation_no=sheet.operation_no,
        well_no=project.well_no if project is not None else sheet.operation_no,
        status=sheet.status.value,
        a5_status=sheet.a5_status,
        a5_remark=sheet.a5_remark,
        contractor_name=contractor.contractor_name if contractor is not None else None,
        team_name=contractor.team_name if contractor is not None else None,
        measures=list((project.measures_jsonb or {}).get("measures", [])) if project is not None else [],
    ))


@router.post("/mock/measure-review/decision", response_model=ApiResponse[A5MockReviewDecisionOut])
def submit_mock_measure_review(
    payload: A5MockReviewDecisionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("a5:sso")),
) -> ApiResponse[A5MockReviewDecisionOut]:
    """Simulate A5 approval/issue or rejection, using the normal state machine."""
    sheet = _get_mock_review_sheet(db, operation_no=payload.operation_no, token=payload.token, current_user=current_user)
    if sheet.status.value != "PENDING_A5":
        raise BusinessException(BAD_REQUEST, "当前工单不处于等待A5审核状态")
    a5_status = "已下发" if payload.decision == "DISPATCH" else "驳回"
    default_remark = "本地A5模拟：措施审核通过并已下发" if payload.decision == "DISPATCH" else "本地A5模拟：措施审核驳回，退回待派工"
    event_at = datetime.now(timezone.utc)
    updated, old_status, new_status, _ = apply_a5_update_by_operation_no(
        db,
        payload.operation_no,
        status=a5_status,
        remark=payload.remark or default_remark,
        progress=1 if payload.decision == "DISPATCH" else 0,
        detail={
            "event_id": f"local-a5-{uuid.uuid4().hex}",
            "event_at": event_at.isoformat(),
            "updated_at": event_at.isoformat(),
            "source": "local_a5_mock",
        },
        source="local_a5_mock",
    )
    if updated is None or old_status is None or new_status is None:
        raise BusinessException(BAD_REQUEST, "A5模拟工单状态更新失败")
    db.commit()
    return success(A5MockReviewDecisionOut(
        operation_no=payload.operation_no,
        old_status=old_status.value,
        new_status=new_status.value,
        message="措施审核已通过并下发" if payload.decision == "DISPATCH" else "措施审核已驳回，工单已退回待派工",
    ))


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
    # Do not trust caller-controlled forwarding headers on this direct callback
    # endpoint; the transport peer is the only IP usable without proxy trust config.
    headers["x-real-ip"] = request.client.host if request.client else ""
    headers.pop("x-forwarded-for", None)
    if x_a5_signature:
        headers["x-a5-signature"] = x_a5_signature
    body = await request.body()
    body_str = body.decode("utf-8") if body else ""
    if not verify_a5_callback_signature(headers, body_str):
        raise BusinessException(BAD_REQUEST, "A5 回调签名验证失败")
    if not is_supported_a5_status(payload.status):
        raise BusinessException(BAD_REQUEST, "A5 回调状态不在允许白名单")
    now = datetime.now(timezone.utc)
    if payload.event_at is not None:
        event_at = payload.event_at if payload.event_at.tzinfo else payload.event_at.replace(tzinfo=timezone.utc)
        if event_at < now.replace(microsecond=0) - timedelta(days=1) or event_at > now + timedelta(minutes=5):
            raise BusinessException(BAD_REQUEST, "A5 回调事件时间已过期或超前")
    if payload.event_id:
        revision = str(payload.version) if payload.version is not None else payload.event_at.isoformat() if payload.event_at else ""
        replay_identity = f"{payload.event_id}:{revision}"
    else:
        replay_identity = hashlib.sha256(body).hexdigest()
    replay_key = f"a5:callback:replay:{replay_identity}"
    replay_fingerprint = hashlib.sha256(f"callback:{replay_identity}".encode("utf-8")).hexdigest()
    processing_key = f"{replay_key}:processing"
    processing_value = {"token": uuid.uuid4().hex, "received_at": now.isoformat()}
    cached_replay = cache_client.get_json(replay_key)
    if cached_replay is not None:
        matched = cached_replay.get("matched", True) if isinstance(cached_replay, dict) else True
        return success(
            {"matched": bool(matched), "operation_no": payload.operation_no, "duplicate": True},
            msg="重复回调已处理",
        )
    if not cache_client.set_lock_json(processing_key, processing_value, expire_seconds=300, nx=True):
        raise BusinessException(CONFLICT, "A5 回调正在处理，请稍后重试")

    try:
        existing_replay = db.scalar(
            select(A5DailyReportRecord).where(A5DailyReportRecord.fingerprint == replay_fingerprint)
        )
        if existing_replay is not None:
            return success(
                {
                    "matched": existing_replay.matched,
                    "operation_no": payload.operation_no,
                    "duplicate": True,
                },
                msg="重复回调已处理",
            )

        sheet, old_status, new_status, changed = apply_a5_update_by_operation_no(
            db,
            payload.operation_no,
            status=payload.status,
            remark=payload.remark,
            detail=payload.model_dump(mode="json"),
            source="callback",
        )
        event_at = payload.event_at or now
        db.add(A5DailyReportRecord(
            operation_sheet_id=sheet.id if sheet is not None else None,
            operation_no=payload.operation_no,
            report_date=event_at.astimezone(BUSINESS_TZ).date() if event_at.tzinfo else event_at.date(),
            fingerprint=replay_fingerprint,
            external_event_id=payload.event_id,
            external_version=payload.version,
            a5_status=payload.status,
            source_updated_at=event_at,
            matched=sheet is not None,
            applied=bool(sheet is not None and changed),
            failure_reason=None if sheet is not None else "未匹配本地修井运行表",
            raw_payload=payload.model_dump(mode="json"),
        ))
        if sheet is None:
            logger.warning(f"A5 回调: 工单 {payload.operation_no} 不存在")
            db.commit()
            try:
                cache_client.set_json(replay_key, {"completed_at": datetime.now(timezone.utc).isoformat(), "matched": False}, expire_seconds=86400)
            except Exception:
                logger.warning("A5回调持久化成功，但Redis重放标记写入失败", exc_info=True)
            return success({"matched": False, "operation_no": payload.operation_no}, msg="工单未匹配")
        db.commit()
        try:
            cache_client.set_json(replay_key, {"completed_at": datetime.now(timezone.utc).isoformat(), "matched": True}, expire_seconds=86400)
        except Exception:
            logger.warning("A5回调持久化成功，但Redis重放标记写入失败", exc_info=True)
    except Exception:
        db.rollback()
        raise
    finally:
        cache_client.delete_json_if_matches(processing_key, processing_value)
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
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("a5:read")),
) -> ApiResponse[A5SyncStatusOut]:
    """查看最近一次 A5 数据同步状态。"""
    cached = cache_client.get_json(A5_SYNC_STATUS_KEY) or {}
    if not cached:
        latest = db.scalar(select(A5SyncBatch).order_by(A5SyncBatch.started_at.desc()).limit(1))
        if latest is not None:
            cached = {
                "last_sync_time": latest.finished_at or latest.started_at,
                "last_sync_status": latest.status.lower(),
                "last_sync_message": latest.error_message or f"日报更新 {latest.updated_count} 条",
                "is_running": latest.status == "RUNNING",
            }
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    sync_count_today = cache_client.get_json(f"{A5_SYNC_COUNT_PREFIX}{today}") or cached.get("sync_count_today", 0)
    return success(A5SyncStatusOut(
        last_sync_time=cached.get("last_sync_time"),
        last_sync_status=cached.get("last_sync_status", "unknown"),
        last_sync_message=cached.get("last_sync_message", ""),
        sync_count_today=int(sync_count_today or 0),
        is_running=bool(cached.get("is_running", False)),
    ))


@router.get("/sync/logs", response_model=ApiResponse[list[A5SyncBatchOut]])
def sync_logs(
    limit: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("a5:read")),
) -> ApiResponse[list[A5SyncBatchOut]]:
    safe_limit = max(1, min(limit, 100))
    rows = db.scalars(select(A5SyncBatch).order_by(A5SyncBatch.started_at.desc()).limit(safe_limit)).all()
    return success([A5SyncBatchOut.model_validate(row) for row in rows])


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
        await full_sync(db, sync_type="MANUAL")
        return success(A5SyncTriggerOut(
            task_id=task_id,
            message="本地同步已执行",
        ), msg="同步已执行")

    task = sync_a5_data_task.delay("MANUAL")
    return success(A5SyncTriggerOut(
        task_id=task.id,
        message="A5 数据同步任务已提交",
    ), msg="同步已触发")
