from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.analytics_alert import AnalyticsAlertCreate, AnalyticsAlertQuery, AnalyticsAlertUpdate
from app.schemas.response import ApiResponse, success
from app.services.analytics_alert_service import list_alerts, patch_alert, upsert_alert

router = APIRouter(prefix="/analytics-alerts", tags=["统计告警"])


@router.get("", response_model=ApiResponse[dict])
def get_alerts(
    query: AnalyticsAlertQuery = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("analytics:alert:read")),
) -> ApiResponse[dict]:
    rows, total = list_alerts(db, query)
    return success({"total": total, "items": rows})


@router.post("", response_model=ApiResponse[dict])
def create_alert(
    payload: AnalyticsAlertCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("analytics:alert:handle")),
) -> ApiResponse[dict]:
    return success(upsert_alert(db, payload))


@router.patch("/{alert_id}", response_model=ApiResponse[dict])
def update_alert(
    alert_id: int,
    payload: AnalyticsAlertUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("analytics:alert:handle")),
) -> ApiResponse[dict]:
    return success(patch_alert(db, alert_id, payload, operator_id=user.id))
