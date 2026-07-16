from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.models.material import MaterialRequirement, MaterialRequirementStatus
from app.models.workover import WorkoverOperationSheet, WorkoverProjectPool
from app.schemas.material import MaterialRequirementCreate, MaterialRequirementQuery, MaterialRequirementUpdate
from app.services.data_scope_service import DataScope, reporting_unit_scope_predicate

BUSINESS_TYPE = "material_requirement"


class MaterialAnalyticsQuery(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    well_no: str | None = None
    status: MaterialRequirementStatus | None = None

ALLOWED_STATUS_TRANSITIONS: dict[MaterialRequirementStatus, set[MaterialRequirementStatus]] = {
    MaterialRequirementStatus.PENDING: {MaterialRequirementStatus.APPROVED, MaterialRequirementStatus.CANCELED},
    MaterialRequirementStatus.APPROVED: {MaterialRequirementStatus.PLANNED, MaterialRequirementStatus.CANCELED},
    MaterialRequirementStatus.PLANNED: {MaterialRequirementStatus.DELIVERED, MaterialRequirementStatus.CANCELED},
    MaterialRequirementStatus.DELIVERED: {MaterialRequirementStatus.ARRIVED, MaterialRequirementStatus.CANCELED},
    MaterialRequirementStatus.ARRIVED: {MaterialRequirementStatus.USED, MaterialRequirementStatus.CANCELED},
    MaterialRequirementStatus.USED: set(),
    MaterialRequirementStatus.CANCELED: set(),
}

MATERIAL_STATUS_ORDER: tuple[MaterialRequirementStatus, ...] = (
    MaterialRequirementStatus.PENDING,
    MaterialRequirementStatus.APPROVED,
    MaterialRequirementStatus.PLANNED,
    MaterialRequirementStatus.DELIVERED,
    MaterialRequirementStatus.ARRIVED,
    MaterialRequirementStatus.USED,
)


def _snapshot(obj: MaterialRequirement) -> dict[str, Any]:
    return {
        "id": obj.id,
        "well_no": obj.well_no,
        "operation_sheet_id": obj.operation_sheet_id,
        "material_name": obj.material_name,
        "specification": obj.specification,
        "quantity": obj.quantity,
        "unit": obj.unit,
        "plan_no": obj.plan_no,
        "warehouse": obj.warehouse,
        "supplier_or_team": obj.supplier_or_team,
        "planned_quantity": obj.planned_quantity,
        "delivered_quantity": obj.delivered_quantity,
        "arrived_quantity": obj.arrived_quantity,
        "used_quantity": obj.used_quantity,
        "delivery_contact": obj.delivery_contact,
        "delivery_phone": obj.delivery_phone,
        "expected_arrival_at": obj.expected_arrival_at.isoformat() if obj.expected_arrival_at else None,
        "exception_reason": obj.exception_reason,
        "source_platform": obj.source_platform,
        "external_material_id": obj.external_material_id,
        "requirement_type": obj.requirement_type.value if hasattr(obj.requirement_type, 'value') else obj.requirement_type,
        "status": obj.status.value if hasattr(obj.status, 'value') else obj.status,
        "remark": obj.remark,
    }


def _ensure_status_transition(current: MaterialRequirementStatus, target: MaterialRequirementStatus) -> None:
    if target == current:
        return
    if target not in ALLOWED_STATUS_TRANSITIONS[current]:
        raise BusinessException(
            CONFLICT,
            f"物料状态不允许从 {current.value} 转换到 {target.value}",
        )


def _apply_filters(stmt: Select[tuple[MaterialRequirement]], query: MaterialRequirementQuery) -> Select[tuple[MaterialRequirement]]:
    if query.well_no:
        stmt = stmt.where(MaterialRequirement.well_no.ilike(f"%{query.well_no}%"))
    if query.operation_sheet_id:
        stmt = stmt.where(MaterialRequirement.operation_sheet_id == query.operation_sheet_id)
    if query.status:
        stmt = stmt.where(MaterialRequirement.status == query.status)
    if query.material_name:
        stmt = stmt.where(MaterialRequirement.material_name.ilike(f"%{query.material_name}%"))
    if query.requirement_type:
        stmt = stmt.where(MaterialRequirement.requirement_type == query.requirement_type)
    if query.has_exception is True:
        stmt = stmt.where(MaterialRequirement.exception_reason.isnot(None), MaterialRequirement.exception_reason != "")
    elif query.has_exception is False:
        stmt = stmt.where((MaterialRequirement.exception_reason.is_(None)) | (MaterialRequirement.exception_reason == ""))
    if query.source_platform:
        stmt = stmt.where(MaterialRequirement.source_platform == query.source_platform)
    return stmt


def _normalize_status(value: MaterialRequirementStatus | str) -> MaterialRequirementStatus:
    return value if isinstance(value, MaterialRequirementStatus) else MaterialRequirementStatus(value)


def _apply_material_scope(stmt: Select, scope: DataScope | None) -> Select:
    if scope is None or scope.is_global:
        return stmt
    return (
        stmt.join(
            WorkoverOperationSheet,
            MaterialRequirement.operation_sheet_id == WorkoverOperationSheet.id,
        )
        .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
        .where(reporting_unit_scope_predicate(scope))
    )


def _material_rollup_status(items: list[MaterialRequirement]) -> MaterialRequirementStatus | None:
    if not items:
        return None
    active_statuses = [
        _normalize_status(item.status)
        for item in items
        if _normalize_status(item.status) != MaterialRequirementStatus.CANCELED
    ]
    if not active_statuses:
        return MaterialRequirementStatus.CANCELED
    if all(status == MaterialRequirementStatus.USED for status in active_statuses):
        return MaterialRequirementStatus.USED
    for status in reversed(MATERIAL_STATUS_ORDER[:-1]):
        if status in active_statuses:
            return status
    return MaterialRequirementStatus.PENDING


def validate_material_quantities(obj: MaterialRequirement) -> None:
    quantities = {
        "需求数量": obj.quantity,
        "计划数量": obj.planned_quantity,
        "出库数量": obj.delivered_quantity,
        "到场数量": obj.arrived_quantity,
        "使用数量": obj.used_quantity,
    }
    for label, value in quantities.items():
        if value is not None and value < 0:
            raise BusinessException(BAD_REQUEST, f"{label}不能小于0")
    if obj.planned_quantity and obj.planned_quantity > obj.quantity:
        raise BusinessException(BAD_REQUEST, "计划数量不能大于需求数量")
    if obj.delivered_quantity and obj.delivered_quantity > (obj.planned_quantity or obj.quantity):
        raise BusinessException(BAD_REQUEST, "出库数量不能大于计划数量")
    if obj.arrived_quantity and obj.arrived_quantity > obj.delivered_quantity:
        raise BusinessException(BAD_REQUEST, "到场数量不能大于出库数量")
    if obj.used_quantity and obj.used_quantity > obj.arrived_quantity:
        raise BusinessException(BAD_REQUEST, "使用数量不能大于到场数量")


def build_material_analytics(items: list[MaterialRequirement]) -> dict[str, Any]:
    total = len(items)
    pending = sum(1 for i in items if _normalize_status(i.status) == MaterialRequirementStatus.PENDING)
    approved = sum(1 for i in items if _normalize_status(i.status) == MaterialRequirementStatus.APPROVED)
    planned = sum(1 for i in items if _normalize_status(i.status) == MaterialRequirementStatus.PLANNED)
    delivered = sum(1 for i in items if _normalize_status(i.status) == MaterialRequirementStatus.DELIVERED)
    arrived = sum(1 for i in items if _normalize_status(i.status) == MaterialRequirementStatus.ARRIVED)
    used = sum(1 for i in items if _normalize_status(i.status) == MaterialRequirementStatus.USED)
    canceled = sum(1 for i in items if _normalize_status(i.status) == MaterialRequirementStatus.CANCELED)
    emergency = sum(1 for i in items if getattr(i.requirement_type, "value", i.requirement_type) == "EMERGENCY")
    exception_count = sum(1 for i in items if bool((i.exception_reason or "").strip()))
    usage_rate = round((used / total) * 100, 2) if total else 0.0

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "planned": planned,
        "delivered": delivered,
        "arrived": arrived,
        "used": used,
        "canceled": canceled,
        "emergency_count": emergency,
        "exception_count": exception_count,
        "usage_rate": usage_rate,
    }


def apply_material_rollup_to_operation_sheet(
    sheet: WorkoverOperationSheet,
    items: list[MaterialRequirement],
) -> None:
    counts = {status.value: 0 for status in MaterialRequirementStatus}
    for item in items:
        counts[_normalize_status(item.status).value] += 1

    rollup_status = _material_rollup_status(items)
    detail = dict(sheet.progress_detail or {})
    detail["material"] = {
        "status": rollup_status.value if rollup_status else "NONE",
        "total": len(items),
        "counts": counts,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    sheet.progress_detail = detail


def sync_operation_sheet_material_rollup(db: Session, operation_sheet_id: int | None) -> None:
    if not operation_sheet_id:
        return
    sheet = db.get(WorkoverOperationSheet, operation_sheet_id)
    if sheet is None:
        return
    items = list(
        db.scalars(
            select(MaterialRequirement).where(MaterialRequirement.operation_sheet_id == operation_sheet_id)
        ).all()
    )
    apply_material_rollup_to_operation_sheet(sheet, items)


def list_material_requirements(
    db: Session,
    query: MaterialRequirementQuery,
    *,
    scope: DataScope | None = None,
) -> tuple[list[MaterialRequirement], int]:
    base_stmt = _apply_material_scope(_apply_filters(select(MaterialRequirement), query), scope)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    rows = db.scalars(
        base_stmt.order_by(MaterialRequirement.created_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return list(rows), total


def get_material_requirement(
    db: Session,
    req_id: int,
    *,
    scope: DataScope | None = None,
) -> MaterialRequirement:
    obj = db.scalar(_apply_material_scope(select(MaterialRequirement).where(MaterialRequirement.id == req_id), scope))
    if obj is None:
        raise BusinessException(BAD_REQUEST, "物料需求记录不存在")
    return obj


def create_material_requirement(
    db: Session,
    payload: MaterialRequirementCreate,
    *,
    scope: DataScope | None = None,
) -> MaterialRequirement:
    data = payload.model_dump(mode="json")
    if scope is not None and data.get("operation_sheet_id"):
        sheet = db.scalar(
            _apply_material_scope(
                select(MaterialRequirement).where(MaterialRequirement.operation_sheet_id == data["operation_sheet_id"]),
                scope,
            )
        )
        if sheet is None:
            allowed_sheet = db.scalar(
                select(WorkoverOperationSheet)
                .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
                .where(WorkoverOperationSheet.id == data["operation_sheet_id"])
                .where(reporting_unit_scope_predicate(scope))
            )
            if allowed_sheet is None:
                raise BusinessException(BAD_REQUEST, "物料需求记录不存在")
    obj = MaterialRequirement(**data)
    validate_material_quantities(obj)
    db.add(obj)
    db.flush()
    sync_operation_sheet_material_rollup(db, obj.operation_sheet_id)
    db.commit()
    db.refresh(obj)
    return obj


def update_material_requirement(
    db: Session,
    req_id: int,
    payload: MaterialRequirementUpdate,
    *,
    scope: DataScope | None = None,
) -> MaterialRequirement:
    obj = get_material_requirement(db, req_id, scope=scope)
    old_operation_sheet_id = obj.operation_sheet_id
    data = payload.model_dump(mode="json", exclude_unset=True)
    for key, value in data.items():
        if key == "status" and value is not None:
            target = _normalize_status(value)
            _ensure_status_transition(obj.status, target)
            # Auto-set timestamps on status transitions
            now = datetime.now(timezone.utc)
            if target == MaterialRequirementStatus.PLANNED:
                obj.planned_at = now
            elif target == MaterialRequirementStatus.DELIVERED:
                obj.delivered_at = now
            elif target == MaterialRequirementStatus.ARRIVED:
                obj.arrived_at = now
            elif target == MaterialRequirementStatus.USED:
                obj.used_at = now
        setattr(obj, key, value)
    validate_material_quantities(obj)
    db.flush()
    if old_operation_sheet_id != obj.operation_sheet_id:
        sync_operation_sheet_material_rollup(db, old_operation_sheet_id)
    sync_operation_sheet_material_rollup(db, obj.operation_sheet_id)
    db.commit()
    db.refresh(obj)
    return obj


def delete_material_requirement(
    db: Session,
    req_id: int,
    *,
    scope: DataScope | None = None,
) -> None:
    obj = get_material_requirement(db, req_id, scope=scope)
    if obj.status not in {MaterialRequirementStatus.PENDING, MaterialRequirementStatus.CANCELED}:
        raise BusinessException(CONFLICT, "只有待处理或已取消的物料需求才能删除")
    operation_sheet_id = obj.operation_sheet_id
    db.delete(obj)
    db.flush()
    sync_operation_sheet_material_rollup(db, operation_sheet_id)
    db.commit()


def get_material_analytics(
    db: Session,
    query: MaterialAnalyticsQuery | str | None = None,
    *,
    well_no: str | None = None,
    scope: DataScope | None = None,
) -> dict[str, Any]:
    if isinstance(query, str):
        query = MaterialAnalyticsQuery(well_no=query)
    else:
        query = query or MaterialAnalyticsQuery(well_no=well_no)
    stmt = _apply_material_scope(select(MaterialRequirement), scope)
    if query.well_no:
        stmt = stmt.where(MaterialRequirement.well_no.ilike(f"%{query.well_no}%"))
    if query.status:
        stmt = stmt.where(MaterialRequirement.status == query.status)
    if query.start_date:
        stmt = stmt.where(MaterialRequirement.created_at >= datetime.combine(query.start_date, time.min))
    if query.end_date:
        stmt = stmt.where(MaterialRequirement.created_at < datetime.combine(query.end_date + timedelta(days=1), time.min))
    items = list(db.scalars(stmt).all())

    return build_material_analytics(items)
