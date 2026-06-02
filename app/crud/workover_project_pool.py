from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.models.approval import ApprovalAction
from app.models.workover import ProjectPoolStatus, WorkoverProjectPool
from app.schemas.workover_project_pool import (
    WorkoverProjectPoolCreate,
    WorkoverProjectPoolQuery,
    WorkoverProjectPoolUpdate,
)
from app.services.audit_service import write_approval_log
from app.services.dictionary_service import ensure_dictionary_values
from app.utils.jsonb import measure_type_filter

BUSINESS_TYPE = "workover_project_pool"


def _project_snapshot(project: WorkoverProjectPool) -> dict[str, Any]:
    return {
        "id": project.id,
        "well_no": project.well_no,
        "well_name": project.well_name,
        "layer": project.layer,
        "fault_description": project.fault_description,
        "territory_unit": project.territory_unit,
        "block_name": project.block_name,
        "report_unit": project.report_unit,
        "production_priority": project.production_priority,
        "status": project.status.value if isinstance(project.status, ProjectPoolStatus) else project.status,
        "reason": project.reason,
        "measures_jsonb": project.measures_jsonb,
        "remark": project.remark,
        "created_by_id": project.created_by_id,
        "is_deleted": project.is_deleted,
    }


def _measure_types(payload: dict[str, Any]) -> set[str]:
    return {
        str(item["measure_type"])
        for item in payload.get("measures", [])
        if isinstance(item, dict) and item.get("measure_type")
    }


def _apply_filters(stmt: Select[tuple[WorkoverProjectPool]], query: WorkoverProjectPoolQuery) -> Select[tuple[WorkoverProjectPool]]:
    stmt = stmt.where(WorkoverProjectPool.is_deleted.is_(False))
    if query.block_name:
        stmt = stmt.where(WorkoverProjectPool.block_name == query.block_name)
    if query.well_no:
        stmt = stmt.where(WorkoverProjectPool.well_no.ilike(f"%{query.well_no}%"))
    if query.status:
        stmt = stmt.where(WorkoverProjectPool.status == query.status)
    if query.measure_type:
        stmt = stmt.where(measure_type_filter(WorkoverProjectPool.measures_jsonb, query.measure_type))
    return stmt


def list_project_pools(db: Session, query: WorkoverProjectPoolQuery) -> tuple[list[WorkoverProjectPool], int]:
    base_stmt = _apply_filters(select(WorkoverProjectPool), query)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    rows = db.scalars(
        base_stmt.order_by(WorkoverProjectPool.created_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return list(rows), total


def list_all_project_pools(db: Session) -> list[WorkoverProjectPool]:
    return list(
        db.scalars(
            select(WorkoverProjectPool)
            .where(WorkoverProjectPool.is_deleted.is_(False))
            .order_by(WorkoverProjectPool.created_at.desc())
        ).all()
    )


def get_project_pool(db: Session, project_id: int) -> WorkoverProjectPool:
    project = db.get(WorkoverProjectPool, project_id)
    if project is None or project.is_deleted:
        raise BusinessException(BAD_REQUEST, "上修项目池记录不存在")
    return project


def create_project_pool(
    db: Session,
    payload: WorkoverProjectPoolCreate,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> WorkoverProjectPool:
    data = payload.model_dump(mode="json")
    ensure_dictionary_values(db, "measure_type", _measure_types(data["measures_jsonb"]))
    project = WorkoverProjectPool(**data, created_by_id=operator_id)
    db.add(project)
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE,
        business_id=project.id,
        node_code="PROJECT_POOL_CREATE",
        action=ApprovalAction.CREATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        after_snapshot=_project_snapshot(project),
    )
    db.commit()
    db.refresh(project)
    return project


def update_project_pool(
    db: Session,
    project_id: int,
    payload: WorkoverProjectPoolUpdate,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> WorkoverProjectPool:
    project = get_project_pool(db, project_id)
    before = _project_snapshot(project)
    data = payload.model_dump(mode="json")
    ensure_dictionary_values(db, "measure_type", _measure_types(data["measures_jsonb"]))
    for key, value in data.items():
        setattr(project, key, value)
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE,
        business_id=project.id,
        node_code="PROJECT_POOL_UPDATE",
        action=ApprovalAction.UPDATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        before_snapshot=before,
        after_snapshot=_project_snapshot(project),
    )
    db.commit()
    db.refresh(project)
    return project


def submit_project_pools(
    db: Session,
    project_ids: list[int],
    *,
    operator_id: int,
    operator_ip: str | None,
    comment: str | None,
) -> list[WorkoverProjectPool]:
    projects = list(
        db.scalars(
            select(WorkoverProjectPool)
            .where(WorkoverProjectPool.id.in_(project_ids), WorkoverProjectPool.is_deleted.is_(False))
            .with_for_update()
        ).all()
    )
    found_ids = {project.id for project in projects}
    missing = set(project_ids) - found_ids
    if missing:
        raise BusinessException(BAD_REQUEST, f"项目池记录不存在: {sorted(missing)}")

    for project in projects:
        if project.status != ProjectPoolStatus.DRAFT:
            raise BusinessException(CONFLICT, f"井号{project.well_no}当前状态不允许提报")

    for project in projects:
        before = _project_snapshot(project)
        project.status = ProjectPoolStatus.PENDING_GEOLOGY_VERIFY
        db.flush()
        write_approval_log(
            db,
            business_type=BUSINESS_TYPE,
            business_id=project.id,
            node_code="PENDING_GEOLOGY_VERIFY",
            action=ApprovalAction.SUBMIT,
            operator_id=operator_id,
            operator_ip=operator_ip,
            comment=comment,
            before_snapshot=before,
            after_snapshot=_project_snapshot(project),
        )
    db.commit()
    for project in projects:
        db.refresh(project)
    return projects


def patch_project_status(
    db: Session,
    project_id: int,
    status: ProjectPoolStatus,
    *,
    operator_id: int,
    operator_ip: str | None,
    comment: str | None,
) -> WorkoverProjectPool:
    project = get_project_pool(db, project_id)
    before = _project_snapshot(project)
    project.status = status
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE,
        business_id=project.id,
        node_code=status.value,
        action=ApprovalAction.UPDATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        comment=comment,
        before_snapshot=before,
        after_snapshot=_project_snapshot(project),
    )
    db.commit()
    db.refresh(project)
    return project


def delete_project_pool(
    db: Session,
    project_id: int,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> None:
    project = get_project_pool(db, project_id)
    before = _project_snapshot(project)
    project.is_deleted = True
    project.status = ProjectPoolStatus.VOIDED
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE,
        business_id=project.id,
        node_code="PROJECT_POOL_VOID",
        action=ApprovalAction.DELETE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        before_snapshot=before,
        after_snapshot=_project_snapshot(project),
    )
    db.commit()
