from datetime import date
from typing import Any

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST
from app.models.completion import WellCompletionRecord
from app.models.rbac import User
from app.models.material import MaterialRequirement, MaterialRequirementStatus
from app.models.workover import OperationStatus, ProjectPoolStatus, WorkoverOperationSheet, WorkoverProjectPool
from app.schemas.completion import WellCompletionCreate, WellCompletionQuery, WellCompletionUpdate
from app.services.data_scope_service import DataScope, apply_workover_operation_scope, reporting_unit_scope_predicate


def _validate_sheet_link(db: Session, sheet_id: int | None, well_no: str, current_user: User | None = None) -> None:
    if sheet_id is None:
        raise BusinessException(BAD_REQUEST, "完井记录必须关联修井运行表")
    stmt = select(WorkoverOperationSheet).join(WorkoverProjectPool).where(WorkoverOperationSheet.id == sheet_id)
    if current_user is not None:
        stmt = apply_workover_operation_scope(stmt, current_user)
    sheet = db.scalar(stmt)
    if sheet is None or sheet.project.well_no != well_no:
        raise BusinessException(BAD_REQUEST, "关联运行表不存在、无权限或井号不一致")
    if sheet.status != OperationStatus.FINISHED:
        raise BusinessException(BAD_REQUEST, "运行表完工后才能登记完井记录")
    if sheet.project.is_deleted or sheet.project.status != ProjectPoolStatus.DISPATCHED:
        raise BusinessException(BAD_REQUEST, "关联项目池未进入已派工生命周期，不能登记完井")
    unfinished_materials = db.scalar(
        select(func.count()).select_from(MaterialRequirement).where(
            MaterialRequirement.operation_sheet_id == sheet.id,
            MaterialRequirement.status.notin_([MaterialRequirementStatus.USED, MaterialRequirementStatus.CANCELED]),
        )
    ) or 0
    if unfinished_materials:
        raise BusinessException(BAD_REQUEST, "仍有未闭环物料需求，不能登记完井")


class CompletionAnalyticsQuery(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    well_no: str | None = None
    measure_type: str | None = None
    team_name: str | None = None
    report_unit: str | None = None


def _apply_filters(stmt: Select[tuple[WellCompletionRecord]], query: WellCompletionQuery) -> Select[tuple[WellCompletionRecord]]:
    if query.well_no:
        stmt = stmt.where(WellCompletionRecord.well_no.ilike(f"%{query.well_no}%"))
    if query.measure_type:
        stmt = stmt.where(WellCompletionRecord.measure_type == query.measure_type)
    if query.start_date:
        stmt = stmt.where(WellCompletionRecord.completion_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(WellCompletionRecord.completion_date <= query.end_date)
    return stmt


def list_completion_records(db: Session, query: WellCompletionQuery, *, current_user: User | None = None) -> tuple[list[WellCompletionRecord], int]:
    base_stmt = _apply_filters(select(WellCompletionRecord).join(WorkoverOperationSheet).join(WorkoverProjectPool), query)
    if current_user is not None:
        base_stmt = apply_workover_operation_scope(base_stmt, current_user)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    rows = db.scalars(
        base_stmt.order_by(WellCompletionRecord.completion_date.desc().nullslast(), WellCompletionRecord.created_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return list(rows), total


def get_completion_record(db: Session, record_id: int, *, current_user: User | None = None) -> WellCompletionRecord:
    stmt = select(WellCompletionRecord).join(WorkoverOperationSheet).join(WorkoverProjectPool).where(WellCompletionRecord.id == record_id)
    if current_user is not None:
        stmt = apply_workover_operation_scope(stmt, current_user)
    obj = db.scalar(stmt)
    if obj is None:
        raise BusinessException(BAD_REQUEST, "完井记录不存在")
    return obj


def _completion_snapshot(record: WellCompletionRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "id": record.id,
        "well_no": record.well_no,
        "measure_type": record.measure_type,
        "completion_date": record.completion_date.isoformat() if record.completion_date else None,
        "team_name": record.team_name,
    }


def apply_completion_rollup_to_operation_sheet(
    sheet: WorkoverOperationSheet,
    records: list[WellCompletionRecord],
) -> None:
    detail = dict(sheet.progress_detail or {})
    latest = records[0] if records else None
    detail["completion"] = {
        "status": "RECORDED" if records else "NONE",
        "total": len(records),
        "latest": _completion_snapshot(latest),
    }
    sheet.progress_detail = detail


def sync_operation_sheet_completion_rollup(db: Session, operation_sheet_id: int | None) -> None:
    if not operation_sheet_id:
        return
    sheet = db.get(WorkoverOperationSheet, operation_sheet_id)
    if sheet is None:
        return
    records = list(
        db.scalars(
            select(WellCompletionRecord)
            .where(WellCompletionRecord.operation_sheet_id == operation_sheet_id)
            .order_by(desc(WellCompletionRecord.completion_date), desc(WellCompletionRecord.created_at))
        ).all()
    )
    apply_completion_rollup_to_operation_sheet(sheet, records)


def create_completion_record(db: Session, payload: WellCompletionCreate, *, current_user: User | None = None) -> WellCompletionRecord:
    data = payload.model_dump(mode="python")
    obj = WellCompletionRecord(**data)
    _validate_sheet_link(db, obj.operation_sheet_id, obj.well_no, current_user)
    db.add(obj)
    db.flush()
    sync_operation_sheet_completion_rollup(db, obj.operation_sheet_id)
    db.commit()
    db.refresh(obj)
    return obj


def update_completion_record(db: Session, record_id: int, payload: WellCompletionUpdate, *, current_user: User | None = None) -> WellCompletionRecord:
    obj = get_completion_record(db, record_id, current_user=current_user)
    operation_sheet_id = obj.operation_sheet_id
    data = payload.model_dump(mode="python", exclude_unset=True)
    for key, value in data.items():
        setattr(obj, key, value)
    _validate_sheet_link(db, obj.operation_sheet_id, obj.well_no, current_user)
    db.flush()
    sync_operation_sheet_completion_rollup(db, operation_sheet_id)
    db.commit()
    db.refresh(obj)
    return obj


def delete_completion_record(db: Session, record_id: int, *, current_user: User | None = None) -> None:
    obj = get_completion_record(db, record_id, current_user=current_user)
    operation_sheet_id = obj.operation_sheet_id
    db.delete(obj)
    db.flush()
    sync_operation_sheet_completion_rollup(db, operation_sheet_id)
    db.commit()


def get_completion_analytics(
    db: Session,
    query: CompletionAnalyticsQuery | None = None,
    *,
    current_user: User | None = None,
    scope: DataScope | None = None,
) -> dict[str, Any]:
    """完井分类统计：按措施类型分组统计。"""
    query = query or CompletionAnalyticsQuery()
    stmt = select(WellCompletionRecord).join(WorkoverOperationSheet).join(WorkoverProjectPool)
    if current_user is not None:
        stmt = apply_workover_operation_scope(stmt, current_user)
    if scope is not None and not scope.is_global:
        stmt = stmt.where(reporting_unit_scope_predicate(scope))
    if query.report_unit and not (
        scope is not None and not scope.is_global and query.report_unit == scope.department
    ):
        stmt = stmt.where(WorkoverProjectPool.report_unit == query.report_unit)
    if query.well_no:
        stmt = stmt.where(WellCompletionRecord.well_no.ilike(f"%{query.well_no}%"))
    if query.measure_type:
        stmt = stmt.where(WellCompletionRecord.measure_type == query.measure_type)
    if query.team_name:
        stmt = stmt.where(WellCompletionRecord.team_name.ilike(f"%{query.team_name}%"))
    if query.start_date:
        stmt = stmt.where(WellCompletionRecord.completion_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(WellCompletionRecord.completion_date <= query.end_date)
    rows = db.scalars(stmt).all()
    by_type: dict[str, int] = {}
    for row in rows:
        by_type[row.measure_type] = by_type.get(row.measure_type, 0) + 1
    return {
        "total": len(rows),
        "by_measure_type": [{"measure_type": k, "count": v} for k, v in sorted(by_type.items(), key=lambda x: -x[1])],
    }
