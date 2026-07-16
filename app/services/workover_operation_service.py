from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.crud.contractor import (
    BUSINESS_TYPE_OPERATION,
    create_operation_sheet,
    get_operation_analytics,
    get_operation_sheet,
    get_operation_sheet_for_user,
    list_operation_sheets,
    select_priority_sheets,
    sync_approved_projects_to_operation_sheets,
    update_sheet_progress,
)
from app.core.exceptions import BusinessException
from app.core.status_codes import CONFLICT
from app.models.completion import WellCompletionRecord
from app.models.material import MaterialRequirement
from app.models.rbac import User
from app.models.workover import ContractorCapacity, OperationStatus, ProjectPoolStatus, WorkoverOperationSheet, WorkoverProjectPool
from app.schemas.contractor import (
    ProgressPatch,
    WorkoverOperationSheetCreate,
    WorkoverOperationSheetQuery,
)
from app.services.data_scope_service import DataScope, apply_workover_operation_scope, reporting_unit_scope_predicate


class OperationAnalyticsQuery(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    well_no: str | None = None
    report_unit: str | None = None
    team_name: str | None = None
    block_name: str | None = None
    status: ProjectPoolStatus | None = None
    measure_type: str | None = None
    material_status: str | None = None


def _material_status(sheet: WorkoverOperationSheet) -> dict[str, Any]:
    material = (sheet.progress_detail or {}).get("material")
    if isinstance(material, dict):
        return {
            "status": material.get("status") or "NONE",
            "total": int(material.get("total") or 0),
            "counts": material.get("counts") or {},
        }
    return {"status": "NONE", "total": 0, "counts": {}}


def _completion_status(db: Session, sheet_id: int, completion_counts: dict[int, int] | None = None) -> dict[str, Any]:
    if completion_counts is None:
        count = db.scalar(
            select(func.count()).select_from(WellCompletionRecord).where(WellCompletionRecord.operation_sheet_id == sheet_id)
        ) or 0
    else:
        count = completion_counts.get(sheet_id, 0)
    return {"status": "RECORDED" if count else "NONE", "total": count}


def _stage(key: str, label: str, status: str, done: bool) -> dict[str, Any]:
    return {"key": key, "label": label, "status": status, "done": done}


def build_closed_loop_status(
    sheet: WorkoverOperationSheet,
    material_status: dict[str, Any],
    completion_status: dict[str, Any],
) -> dict[str, Any]:
    project_status = sheet.project.status.value if getattr(sheet.project.status, "value", None) else str(sheet.project.status)
    operation_status = sheet.status.value if getattr(sheet.status, "value", None) else str(sheet.status)
    material_code = str(material_status.get("status") or "NONE")
    completion_code = str(completion_status.get("status") or "NONE")
    a5_synced = bool(
        sheet.a5_status
        and sheet.last_a5_sync_at
        and sheet.a5_sync_result in {None, "SUCCESS"}
    )
    a5_code = "SYNCED" if a5_synced else "PENDING"

    stages = [
        _stage("project", "项目入库", project_status, project_status in {ProjectPoolStatus.APPROVED.value, ProjectPoolStatus.DISPATCHED.value}),
        _stage("operation", "运行派工", operation_status, operation_status == OperationStatus.FINISHED.value),
        _stage("a5", "A5同步", a5_code, a5_synced),
        _stage("material", "物料保障", material_code, material_code in {"NONE", "ARRIVED", "USED"}),
        _stage("completion", "完井登记", completion_code, completion_code == "RECORDED"),
    ]
    done_count = sum(1 for item in stages if item["done"])
    if done_count == len(stages):
        overall = "COMPLETE"
    elif done_count > 1:
        overall = "IN_PROGRESS"
    else:
        overall = "PENDING"

    return {
        "overall": overall,
        "done_count": done_count,
        "total_count": len(stages),
        "stages": stages,
    }


def enrich_workover_operation_sheet(
    db: Session, sheet: WorkoverOperationSheet, *, completion_counts: dict[int, int] | None = None
) -> dict[str, Any]:
    material_status = _material_status(sheet)
    completion_status = _completion_status(db, sheet.id, completion_counts)
    project = sheet.project
    contractor = sheet.contractor_capacity
    return {
        "id": sheet.id,
        "project_id": sheet.project_id,
        "project_well_no": project.well_no if project else None,
        "project": {
            "id": project.id,
            "well_no": project.well_no,
            "block_name": project.block_name,
            "territory_unit": project.territory_unit,
            "report_unit": project.report_unit,
            "data_source": project.data_source,
            "measures_jsonb": project.measures_jsonb,
            "approved_at": project.approved_at,
        } if project else None,
        "contractor_capacity_id": sheet.contractor_capacity_id,
        "contractor": {
            "id": contractor.id,
            "contractor_name": contractor.contractor_name,
            "team_name": contractor.team_name,
            "report_date": contractor.report_date,
            "status": contractor.status.value if hasattr(contractor.status, "value") else contractor.status,
        } if contractor else None,
        "operation_no": sheet.operation_no,
        "status": sheet.status.value if hasattr(sheet.status, "value") else sheet.status,
        "progress": sheet.progress,
        "planned_start_at": sheet.planned_start_at,
        "planned_end_at": sheet.planned_end_at,
        "actual_start_at": sheet.actual_start_at,
        "actual_end_at": sheet.actual_end_at,
        "progress_detail": sheet.progress_detail,
        "a5_status": sheet.a5_status,
        "a5_remark": sheet.a5_remark,
        "last_a5_sync_at": sheet.last_a5_sync_at,
        "last_a5_report_date": sheet.last_a5_report_date,
        "a5_sync_result": sheet.a5_sync_result,
        "a5_sync_error": sheet.a5_sync_error,
        "material_status": material_status,
        "completion_status": completion_status,
        "closed_loop_status": build_closed_loop_status(sheet, material_status, completion_status),
        "created_at": sheet.created_at,
        "updated_at": sheet.updated_at,
    }


def list_workover_operation_sheets(
    db: Session,
    query: WorkoverOperationSheetQuery,
    *,
    operator_id: int | None = None,
    operator_ip: str | None = None,
    current_user: User | None = None,
) -> tuple[list[dict[str, Any]], int]:
    rows, total = list_operation_sheets(db, query, current_user=current_user)
    sheet_ids = [row.id for row in rows]
    completion_counts = {
        sheet_id: count
        for sheet_id, count in db.execute(
            select(WellCompletionRecord.operation_sheet_id, func.count())
            .where(WellCompletionRecord.operation_sheet_id.in_(sheet_ids))
            .group_by(WellCompletionRecord.operation_sheet_id)
        )
    } if sheet_ids else {}
    return [enrich_workover_operation_sheet(db, row, completion_counts=completion_counts) for row in rows], total


def list_priority_operation_sheets(
    db: Session,
    *,
    operator_id: int | None = None,
    operator_ip: str | None = None,
    current_user: User | None = None,
) -> list[dict[str, Any]]:
    return [enrich_workover_operation_sheet(db, row) for row in select_priority_sheets(db, current_user=current_user)]


def create_workover_operation_sheet(
    db: Session,
    payload: WorkoverOperationSheetCreate,
    *,
    operator_id: int,
    operator_ip: str | None,
    current_user: User | None = None,
) -> dict[str, Any]:
    sheet = create_operation_sheet(
        db, payload, operator_id=operator_id, operator_ip=operator_ip, current_user=current_user
    )
    return enrich_workover_operation_sheet(db, sheet)


def get_workover_operation_sheet(
    db: Session,
    sheet_id: int,
    *,
    current_user: User | None = None,
    scope: DataScope | None = None,
) -> dict[str, Any]:
    if current_user is None:
        sheet = get_operation_sheet(db, sheet_id)
    else:
        sheet = get_operation_sheet_for_user(db, sheet_id, current_user)
    return enrich_workover_operation_sheet(db, sheet)


def update_workover_operation_progress(
    db: Session,
    sheet_id: int,
    payload: ProgressPatch,
    *,
    operator_id: int,
    operator_ip: str | None,
    current_user: User | None = None,
) -> dict[str, Any]:
    # A5 daily reports are the sole authority for construction state and
    # progress.  Keep this compatibility boundary fail-closed so no caller can
    # bypass the A5 review/report chain through an old manual-progress API.
    raise BusinessException(CONFLICT, "施工状态和进度由A5日报同步，本系统不支持手工更新")


def build_workover_operation_dashboard(
    db: Session,
    query: OperationAnalyticsQuery | None = None,
    *,
    current_user: User | None = None,
    scope: DataScope | None = None,
) -> dict[str, Any]:
    if query is None:
        base = get_operation_analytics(db, current_user=current_user)
        id_stmt = select(WorkoverOperationSheet.id).join(WorkoverProjectPool)
        if current_user is not None:
            id_stmt = apply_workover_operation_scope(id_stmt, current_user)
        if scope is not None and not scope.is_global:
            id_stmt = id_stmt.where(reporting_unit_scope_predicate(scope))
        sheet_ids = list(db.scalars(id_stmt).all())
    else:
        stmt = select(WorkoverOperationSheet).join(WorkoverProjectPool).outerjoin(ContractorCapacity)
        if current_user is not None:
            stmt = apply_workover_operation_scope(stmt, current_user)
        if scope is not None and not scope.is_global:
            stmt = stmt.where(reporting_unit_scope_predicate(scope))
        if query.well_no:
            stmt = stmt.where(WorkoverProjectPool.well_no.ilike(f"%{query.well_no}%"))
        if query.report_unit and not (
            scope is not None and not scope.is_global and query.report_unit == scope.department
        ):
            stmt = stmt.where(WorkoverProjectPool.report_unit.ilike(f"%{query.report_unit}%"))
        if query.team_name:
            stmt = stmt.where(ContractorCapacity.team_name.ilike(f"%{query.team_name}%"))
        if query.block_name:
            stmt = stmt.where(WorkoverProjectPool.block_name == query.block_name)
        if query.status:
            stmt = stmt.where(WorkoverProjectPool.status == query.status)
        if query.measure_type:
            stmt = stmt.where(cast(WorkoverProjectPool.measures_jsonb, String).ilike(f"%{query.measure_type}%"))
        if query.start_date:
            stmt = stmt.where(WorkoverOperationSheet.created_at >= datetime.combine(query.start_date, time.min))
        if query.end_date:
            stmt = stmt.where(WorkoverOperationSheet.created_at < datetime.combine(query.end_date + timedelta(days=1), time.min))
        sheets = list(db.scalars(stmt).all())
        counts = {status.value: 0 for status in OperationStatus}
        teams: dict[str, int] = {}
        measures: dict[str, int] = {}
        anomaly_count = 0
        for sheet in sheets:
            counts[getattr(sheet.status, "value", sheet.status)] += 1
            if sheet.contractor_capacity and sheet.contractor_capacity.team_name:
                team = sheet.contractor_capacity.team_name
                teams[team] = teams.get(team, 0) + 1
            for measure in (sheet.project.measures_jsonb or {}).get("measures", []):
                measure_type = measure.get("measure_type") if isinstance(measure, dict) else None
                if measure_type:
                    measures[measure_type] = measures.get(measure_type, 0) + 1
            if str(sheet.a5_status or "").upper() in {"ANOMALY", "ERROR", "EXCEPTION", "FAILED"}:
                anomaly_count += 1
        total = len(sheets)
        active = counts[OperationStatus.PENDING_A5.value] + counts[OperationStatus.DISPATCHED.value] + counts[OperationStatus.WORKING.value] + counts[OperationStatus.FINISHED.value]
        base = {
            "total_sheets": total,
            "status_distribution": {
                "waiting_dispatch": counts[OperationStatus.WAITING_DISPATCH.value],
                "pending_a5": counts[OperationStatus.PENDING_A5.value],
                "dispatched": counts[OperationStatus.DISPATCHED.value],
                "working": counts[OperationStatus.WORKING.value],
                "finished": counts[OperationStatus.FINISHED.value],
                "canceled": counts[OperationStatus.CANCELED.value],
            },
            "dispatch_rate": round(active / total * 100, 1) if total else 0,
            "completion_rate": round(counts[OperationStatus.FINISHED.value] / total * 100, 1) if total else 0,
            "team_workload": sorted(
                [{"team_name": team, "sheet_count": count} for team, count in teams.items()],
                key=lambda item: -item["sheet_count"],
            ),
            "measure_type_distribution": sorted(
                [{"measure_type": key, "count": value} for key, value in measures.items()],
                key=lambda item: -item["count"],
            ),
            "anomaly_count": anomaly_count,
        }
    material_stmt = select(func.count()).select_from(MaterialRequirement)
    completion_stmt = select(func.count()).select_from(WellCompletionRecord)
    if query is not None:
        sheet_ids = [sheet.id for sheet in sheets]
    a5_stmt = select(func.count()).select_from(WorkoverOperationSheet).where(
        WorkoverOperationSheet.a5_status.is_not(None),
        WorkoverOperationSheet.last_a5_sync_at.is_not(None),
        or_(WorkoverOperationSheet.a5_sync_result == "SUCCESS", WorkoverOperationSheet.a5_sync_result.is_(None)),
        WorkoverOperationSheet.id.in_(sheet_ids),
    )
    material_stmt = material_stmt.where(MaterialRequirement.operation_sheet_id.in_(sheet_ids))
    completion_stmt = completion_stmt.where(WellCompletionRecord.operation_sheet_id.in_(sheet_ids))
    if query is not None:
        if query.material_status:
            material_stmt = material_stmt.where(MaterialRequirement.status == query.material_status)
        if query.measure_type:
            completion_stmt = completion_stmt.where(WellCompletionRecord.measure_type == query.measure_type)
        if query.team_name:
            completion_stmt = completion_stmt.where(WellCompletionRecord.team_name.ilike(f"%{query.team_name}%"))
        if query.start_date:
            completion_stmt = completion_stmt.where(WellCompletionRecord.completion_date >= query.start_date)
            material_stmt = material_stmt.where(MaterialRequirement.created_at >= datetime.combine(query.start_date, time.min))
        if query.end_date:
            completion_stmt = completion_stmt.where(WellCompletionRecord.completion_date <= query.end_date)
            material_stmt = material_stmt.where(MaterialRequirement.created_at < datetime.combine(query.end_date + timedelta(days=1), time.min))
    total_materials = db.scalar(material_stmt) or 0
    total_completions = db.scalar(completion_stmt) or 0
    a5_synced = db.scalar(a5_stmt) or 0
    waiting = base.get("status_distribution", {}).get("waiting_dispatch", 0)
    pending_a5 = base.get("status_distribution", {}).get("pending_a5", 0)
    working = base.get("status_distribution", {}).get("working", 0)
    finished = base.get("status_distribution", {}).get("finished", 0)
    return {
        **base,
        "business_type": BUSINESS_TYPE_OPERATION,
        "runtime_focus": {
            "waiting": waiting,
            "pending_a5": pending_a5,
            "working": working,
            "finished": finished,
            "material_total": total_materials,
            "completion_total": total_completions,
            "a5_synced": a5_synced,
        },
        "status_tabs": [status.value for status in OperationStatus],
    }
