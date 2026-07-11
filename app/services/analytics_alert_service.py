from __future__ import annotations

from sqlalchemy.orm import Session

from app.crud.analytics_alert import create_or_update_analytics_alert, list_analytics_alerts, update_analytics_alert
from app.schemas.analytics_alert import AnalyticsAlertCreate, AnalyticsAlertOut, AnalyticsAlertQuery, AnalyticsAlertUpdate


def _to_out(obj) -> AnalyticsAlertOut:
    return AnalyticsAlertOut.model_validate(obj)


def list_alerts(db: Session, query: AnalyticsAlertQuery) -> tuple[list[AnalyticsAlertOut], int]:
    rows, total = list_analytics_alerts(db, query)
    return [_to_out(row) for row in rows], total


def upsert_alert(db: Session, payload: AnalyticsAlertCreate) -> AnalyticsAlertOut:
    return _to_out(create_or_update_analytics_alert(db, payload))


def patch_alert(db: Session, alert_id: int, payload: AnalyticsAlertUpdate, *, operator_id: int | None = None) -> AnalyticsAlertOut:
    return _to_out(update_analytics_alert(db, alert_id, payload, operator_id=operator_id))
