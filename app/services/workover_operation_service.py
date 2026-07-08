from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.contractor import (
    BUSINESS_TYPE_OPERATION,
    create_operation_sheet,
    get_operation_analytics,
    get_operation_sheet,
    list_operation_sheets,
    select_priority_sheets,
    sync_approved_projects_to_operation_sheets,
    update_sheet_progress,
)
from app.models.completion import WellCompletionRecord
from app.models.material import MaterialRequirement
from app.models.workover import OperationStatus, WorkoverOperationSheet
from app.schemas.contractor import (
    ProgressPatch,
    WorkoverOperationSheetCreate,
    WorkoverOperationSheetQuery,
)


def _material_status(sheet: WorkoverOperationSheet) -> dict[str, Any]:
    material = (sheet.progress_detail or {}).get("material")
    if isinstance(material, dict):
        return {
            "status": material.get("status") or "NONE",
            "total": int(material.get("total") or 0),
            "counts": material.get("counts") or {},
        }
    return {"status": "NONE", "total": 0, "counts": {}}


def _completion_status(db: Session, sheet_id: int) -> dict[str, Any]:
    count = db.scalar(
        select(func.count()).select_from(WellCompletionRecord).where(WellCompletionRecord.operation_sheet_id == sheet_id)
    ) or 0
    return {"status": "RECORDED" if count else "NONE", "total": count}


def enrich_workover_operation_sheet(db: Session, sheet: WorkoverOperationSheet) -> dict[str, Any]:
    return {
        "id": sheet.id,
        "project_id": sheet.project_id,
        "contractor_capacity_id": sheet.contractor_capacity_id,
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
        "material_status": _material_status(sheet),
        "completion_status": _completion_status(db, sheet.id),
        "created_at": sheet.created_at,
        "updated_at": sheet.updated_at,
    }


def list_workover_operation_sheets(
    db: Session,
    query: WorkoverOperationSheetQuery,
    *,
    operator_id: int | None = None,
    operator_ip: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    sync_approved_projects_to_operation_sheets(db, operator_id=operator_id, operator_ip=operator_ip)
    rows, total = list_operation_sheets(db, query)
    return [enrich_workover_operation_sheet(db, row) for row in rows], total


def list_priority_operation_sheets(
    db: Session,
    *,
    operator_id: int | None = None,
    operator_ip: str | None = None,
) -> list[dict[str, Any]]:
    sync_approved_projects_to_operation_sheets(db, operator_id=operator_id, operator_ip=operator_ip)
    return [enrich_workover_operation_sheet(db, row) for row in select_priority_sheets(db)]


def create_workover_operation_sheet(
    db: Session,
    payload: WorkoverOperationSheetCreate,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> dict[str, Any]:
    sheet = create_operation_sheet(db, payload, operator_id=operator_id, operator_ip=operator_ip)
    return enrich_workover_operation_sheet(db, sheet)


def get_workover_operation_sheet(db: Session, sheet_id: int) -> dict[str, Any]:
    return enrich_workover_operation_sheet(db, get_operation_sheet(db, sheet_id))


def update_workover_operation_progress(
    db: Session,
    sheet_id: int,
    payload: ProgressPatch,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> dict[str, Any]:
    sheet = update_sheet_progress(db, sheet_id, payload, operator_id=operator_id, operator_ip=operator_ip)
    return enrich_workover_operation_sheet(db, sheet)


def build_workover_operation_dashboard(db: Session) -> dict[str, Any]:
    base = get_operation_analytics(db)
    total_materials = db.scalar(select(func.count()).select_from(MaterialRequirement)) or 0
    total_completions = db.scalar(select(func.count()).select_from(WellCompletionRecord)) or 0
    a5_synced = db.scalar(
        select(func.count()).select_from(WorkoverOperationSheet).where(WorkoverOperationSheet.a5_status.is_not(None))
    ) or 0
    waiting = base.get("status_distribution", {}).get("waiting_dispatch", 0)
    working = base.get("status_distribution", {}).get("working", 0)
    finished = base.get("status_distribution", {}).get("finished", 0)
    return {
        **base,
        "business_type": BUSINESS_TYPE_OPERATION,
        "runtime_focus": {
            "waiting": waiting,
            "working": working,
            "finished": finished,
            "material_total": total_materials,
            "completion_total": total_completions,
            "a5_synced": a5_synced,
        },
        "status_tabs": [status.value for status in OperationStatus],
    }
