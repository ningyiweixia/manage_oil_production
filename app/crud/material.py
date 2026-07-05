from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.models.material import MaterialRequirement, MaterialRequirementStatus
from app.schemas.material import MaterialRequirementCreate, MaterialRequirementQuery, MaterialRequirementUpdate

BUSINESS_TYPE = "material_requirement"

ALLOWED_STATUS_TRANSITIONS: dict[MaterialRequirementStatus, set[MaterialRequirementStatus]] = {
    MaterialRequirementStatus.PENDING: {MaterialRequirementStatus.APPROVED, MaterialRequirementStatus.CANCELED},
    MaterialRequirementStatus.APPROVED: {MaterialRequirementStatus.PLANNED, MaterialRequirementStatus.CANCELED},
    MaterialRequirementStatus.PLANNED: {MaterialRequirementStatus.DELIVERED, MaterialRequirementStatus.CANCELED},
    MaterialRequirementStatus.DELIVERED: {MaterialRequirementStatus.ARRIVED, MaterialRequirementStatus.CANCELED},
    MaterialRequirementStatus.ARRIVED: {MaterialRequirementStatus.USED},
    MaterialRequirementStatus.USED: set(),
    MaterialRequirementStatus.CANCELED: set(),
}


def _snapshot(obj: MaterialRequirement) -> dict[str, Any]:
    return {
        "id": obj.id,
        "well_no": obj.well_no,
        "operation_sheet_id": obj.operation_sheet_id,
        "material_name": obj.material_name,
        "specification": obj.specification,
        "quantity": obj.quantity,
        "unit": obj.unit,
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
    return stmt


def list_material_requirements(db: Session, query: MaterialRequirementQuery) -> tuple[list[MaterialRequirement], int]:
    base_stmt = _apply_filters(select(MaterialRequirement), query)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    rows = db.scalars(
        base_stmt.order_by(MaterialRequirement.created_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return list(rows), total


def get_material_requirement(db: Session, req_id: int) -> MaterialRequirement:
    obj = db.get(MaterialRequirement, req_id)
    if obj is None:
        raise BusinessException(BAD_REQUEST, "物料需求记录不存在")
    return obj


def create_material_requirement(
    db: Session,
    payload: MaterialRequirementCreate,
) -> MaterialRequirement:
    data = payload.model_dump(mode="json")
    obj = MaterialRequirement(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_material_requirement(
    db: Session,
    req_id: int,
    payload: MaterialRequirementUpdate,
) -> MaterialRequirement:
    obj = get_material_requirement(db, req_id)
    data = payload.model_dump(mode="json", exclude_unset=True)
    for key, value in data.items():
        if key == "status" and value is not None:
            from app.models.material import MaterialRequirementStatus as MRS
            target = MRS(value)
            _ensure_status_transition(obj.status, target)
            # Auto-set timestamps on status transitions
            now = datetime.now(timezone.utc)
            if target == MaterialRequirementStatus.DELIVERED:
                obj.delivered_at = now
            elif target == MaterialRequirementStatus.ARRIVED:
                obj.arrived_at = now
            elif target == MaterialRequirementStatus.USED:
                obj.used_at = now
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_material_requirement(
    db: Session,
    req_id: int,
) -> None:
    obj = get_material_requirement(db, req_id)
    if obj.status not in {MaterialRequirementStatus.PENDING, MaterialRequirementStatus.CANCELED}:
        raise BusinessException(CONFLICT, "只有待处理或已取消的物料需求才能删除")
    db.delete(obj)
    db.commit()


def get_material_analytics(db: Session, well_no: str | None = None) -> dict[str, Any]:
    stmt = select(MaterialRequirement)
    if well_no:
        stmt = stmt.where(MaterialRequirement.well_no.ilike(f"%{well_no}%"))
    items = list(db.scalars(stmt).all())

    total = len(items)
    pending = sum(1 for i in items if i.status == MaterialRequirementStatus.PENDING)
    approved = sum(1 for i in items if i.status == MaterialRequirementStatus.APPROVED)
    planned = sum(1 for i in items if i.status == MaterialRequirementStatus.PLANNED)
    delivered = sum(1 for i in items if i.status == MaterialRequirementStatus.DELIVERED)
    arrived = sum(1 for i in items if i.status == MaterialRequirementStatus.ARRIVED)
    used = sum(1 for i in items if i.status == MaterialRequirementStatus.USED)
    canceled = sum(1 for i in items if i.status == MaterialRequirementStatus.CANCELED)
    emergency = sum(1 for i in items if i.requirement_type.value == "EMERGENCY")

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
    }
