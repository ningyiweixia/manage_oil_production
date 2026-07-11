from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.models.analytics import AnalyticsAlert, AnalyticsAlertStatus
from app.schemas.analytics_alert import AnalyticsAlertCreate, AnalyticsAlertQuery, AnalyticsAlertUpdate


ALLOWED_STATUS_TRANSITIONS: dict[AnalyticsAlertStatus, set[AnalyticsAlertStatus]] = {
    AnalyticsAlertStatus.OPEN: {AnalyticsAlertStatus.PROCESSING, AnalyticsAlertStatus.CLOSED},
    AnalyticsAlertStatus.PROCESSING: {AnalyticsAlertStatus.CLOSED},
    AnalyticsAlertStatus.CLOSED: set(),
}


def _apply_filters(stmt, query: AnalyticsAlertQuery):
    if query.status:
        stmt = stmt.where(AnalyticsAlert.status == query.status)
    if query.severity:
        stmt = stmt.where(AnalyticsAlert.severity == query.severity)
    if query.assignee_id:
        stmt = stmt.where(AnalyticsAlert.assignee_id == query.assignee_id)
    if query.keyword:
        keyword = f"%{query.keyword}%"
        stmt = stmt.where(or_(AnalyticsAlert.title.ilike(keyword), AnalyticsAlert.message.ilike(keyword), AnalyticsAlert.alert_key.ilike(keyword)))
    return stmt


def list_analytics_alerts(db: Session, query: AnalyticsAlertQuery) -> tuple[list[AnalyticsAlert], int]:
    base_stmt = _apply_filters(select(AnalyticsAlert), query)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    rows = db.scalars(
        base_stmt.order_by(AnalyticsAlert.opened_at.desc().nullslast(), AnalyticsAlert.created_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return list(rows), total


def get_analytics_alert(db: Session, alert_id: int) -> AnalyticsAlert:
    obj = db.get(AnalyticsAlert, alert_id)
    if obj is None:
        raise BusinessException(BAD_REQUEST, "告警不存在")
    return obj


def create_or_update_analytics_alert(db: Session, payload: AnalyticsAlertCreate) -> AnalyticsAlert:
    obj = db.scalar(select(AnalyticsAlert).where(AnalyticsAlert.alert_key == payload.alert_key).limit(1))
    now = datetime.now(timezone.utc)
    if obj is None:
        obj = AnalyticsAlert(alert_key=payload.alert_key, opened_at=now)
        db.add(obj)
    obj.title = payload.title
    obj.message = payload.message
    obj.severity = payload.severity
    obj.source_module = payload.source_module
    obj.business_type = payload.business_type
    obj.business_id = payload.business_id
    obj.status = payload.status
    obj.assignee_id = payload.assignee_id
    obj.assignee_name = payload.assignee_name
    obj.remark = payload.remark
    if obj.status == AnalyticsAlertStatus.PROCESSING and obj.processed_at is None:
        obj.processed_at = now
    if obj.status == AnalyticsAlertStatus.CLOSED and obj.closed_at is None:
        obj.closed_at = now
    db.flush()
    db.commit()
    db.refresh(obj)
    return obj


def update_analytics_alert(db: Session, alert_id: int, payload: AnalyticsAlertUpdate, *, operator_id: int | None = None) -> AnalyticsAlert:
    obj = get_analytics_alert(db, alert_id)
    target_status = payload.status or obj.status
    if target_status != obj.status and target_status not in ALLOWED_STATUS_TRANSITIONS[obj.status]:
        raise BusinessException(CONFLICT, f"不允许从 {obj.status.value} 流转到 {target_status.value}")

    now = datetime.now(timezone.utc)
    if payload.status is not None:
        obj.status = payload.status
        if payload.status == AnalyticsAlertStatus.PROCESSING and obj.processed_at is None:
            obj.processed_at = now
            obj.processed_by_id = operator_id
        elif payload.status == AnalyticsAlertStatus.CLOSED:
            if obj.processed_at is None:
                obj.processed_at = now
                obj.processed_by_id = operator_id
            obj.closed_at = now
            obj.closed_by_id = operator_id
    if payload.assignee_id is not None:
        obj.assignee_id = payload.assignee_id
    if payload.assignee_name is not None:
        obj.assignee_name = payload.assignee_name
    if payload.remark is not None:
        obj.remark = payload.remark
    db.flush()
    db.commit()
    db.refresh(obj)
    return obj
