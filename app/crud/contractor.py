import uuid
from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessException
from app.core.redis import cache_client
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.models.approval import ApprovalAction
from app.models.workover import (
    ContractorCapacity,
    ContractorCapacitySourceType,
    ContractorCapacityStatus,
    ContractorCapacitySyncLog,
    ContractorCapacitySyncResultStatus,
    ContractorCapacitySyncStatus,
    ContractorCapacitySyncType,
    OperationStatus,
    ProjectPoolStatus,
    WorkoverOperationSheet,
    WorkoverProjectPool,
)
from app.schemas.contractor import (
    ContractorCapacityCreate,
    ContractorCapacityQuery,
    ContractorCapacitySyncLogQuery,
    ContractorCapacityUpdate,
    DispatchPayload,
    ProgressPatch,
    WorkoverOperationSheetCreate,
    WorkoverOperationSheetQuery,
    WorkoverOperationSheetUpdate,
)
from app.services.audit_service import write_approval_log
from app.services.dictionary_service import ensure_dictionary_values
from app.services.contractor_external_client import ContractorExternalClient, ContractorExternalClientError, ExternalContractorTeam

BUSINESS_TYPE_CONTRACTOR = "contractor_capacity"
BUSINESS_TYPE_OPERATION = "workover_operation_sheet"

LOCK_PREFIX = "dispatch:lock:"
LOCK_TTL = 30  # seconds


def _contractor_snapshot(obj: ContractorCapacity) -> dict[str, Any]:
    return {
        "id": obj.id,
        "contractor_name": obj.contractor_name,
        "team_name": obj.team_name,
        "report_date": str(obj.report_date) if obj.report_date else None,
        "available_count": obj.available_count,
        "status": obj.status.value if isinstance(obj.status, ContractorCapacityStatus) else obj.status,
        "capability_tags": obj.capability_tags,
        "external_system_id": obj.external_system_id,
        "external_status": obj.external_status,
        "source_type": obj.source_type.value if isinstance(obj.source_type, ContractorCapacitySourceType) else obj.source_type,
        "sync_status": obj.sync_status.value if isinstance(obj.sync_status, ContractorCapacitySyncStatus) else obj.sync_status,
        "last_synced_at": obj.last_synced_at.isoformat() if obj.last_synced_at else None,
        "sync_error_message": obj.sync_error_message,
        "contact_name": obj.contact_name,
        "contact_phone": obj.contact_phone,
        "qualification_expire_at": str(obj.qualification_expire_at) if obj.qualification_expire_at else None,
        "equipment_summary": obj.equipment_summary,
    }


def _sheet_snapshot(obj: WorkoverOperationSheet) -> dict[str, Any]:
    return {
        "id": obj.id,
        "project_id": obj.project_id,
        "contractor_capacity_id": obj.contractor_capacity_id,
        "operation_no": obj.operation_no,
        "status": obj.status.value if isinstance(obj.status, OperationStatus) else obj.status,
        "progress": obj.progress,
        "planned_start_at": obj.planned_start_at.isoformat() if obj.planned_start_at else None,
        "planned_end_at": obj.planned_end_at.isoformat() if obj.planned_end_at else None,
    }


def _apply_contractor_filters(stmt: Select[tuple[ContractorCapacity]], query: ContractorCapacityQuery) -> Select[tuple[ContractorCapacity]]:
    if query.contractor_name:
        stmt = stmt.where(ContractorCapacity.contractor_name.ilike(f"%{query.contractor_name}%"))
    if query.team_name:
        stmt = stmt.where(ContractorCapacity.team_name.ilike(f"%{query.team_name}%"))
    if query.report_date:
        stmt = stmt.where(ContractorCapacity.report_date == query.report_date)
    if query.status:
        stmt = stmt.where(ContractorCapacity.status == query.status)
    if query.source_type:
        stmt = stmt.where(ContractorCapacity.source_type == query.source_type)
    if query.sync_status:
        stmt = stmt.where(ContractorCapacity.sync_status == query.sync_status)
    if query.capability_tag:
        stmt = stmt.where(ContractorCapacity.capability_tags[query.capability_tag].as_boolean().is_(True))
    return stmt


def _apply_sheet_filters(stmt: Select[tuple[WorkoverOperationSheet]], query: WorkoverOperationSheetQuery) -> Select[tuple[WorkoverOperationSheet]]:
    if query.status:
        stmt = stmt.where(WorkoverOperationSheet.status == query.status)
    if query.project_id:
        stmt = stmt.where(WorkoverOperationSheet.project_id == query.project_id)
    if query.contractor_capacity_id:
        stmt = stmt.where(WorkoverOperationSheet.contractor_capacity_id == query.contractor_capacity_id)
    if query.well_no:
        stmt = stmt.where(WorkoverProjectPool.well_no.ilike(f"%{query.well_no}%"))
    if query.block_name:
        stmt = stmt.where(WorkoverProjectPool.block_name.ilike(f"%{query.block_name}%"))
    if query.contractor_keyword:
        keyword = f"%{query.contractor_keyword}%"
        stmt = stmt.where(
            or_(
                ContractorCapacity.contractor_name.ilike(keyword),
                ContractorCapacity.team_name.ilike(keyword),
            )
        )
    if query.start_date:
        start_at = datetime.combine(query.start_date, time.min)
        stmt = stmt.where(
            or_(
                WorkoverOperationSheet.planned_start_at >= start_at,
                WorkoverOperationSheet.actual_start_at >= start_at,
            )
        )
    if query.end_date:
        end_at = datetime.combine(query.end_date, time.max)
        stmt = stmt.where(
            or_(
                WorkoverOperationSheet.planned_end_at <= end_at,
                WorkoverOperationSheet.actual_end_at <= end_at,
            )
        )
    return stmt


def list_contractor_capacities(db: Session, query: ContractorCapacityQuery) -> tuple[list[ContractorCapacity], int]:
    base_stmt = _apply_contractor_filters(select(ContractorCapacity).options(selectinload(ContractorCapacity.operations)), query)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    rows = db.scalars(
        base_stmt.order_by(ContractorCapacity.report_date.desc(), ContractorCapacity.created_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return list(rows), total


def get_contractor_capacity(db: Session, contractor_id: int) -> ContractorCapacity:
    obj = db.get(ContractorCapacity, contractor_id)
    if obj is None:
        raise BusinessException(BAD_REQUEST, "承包商运力记录不存在")
    return obj


def create_contractor_capacity(
    db: Session,
    payload: ContractorCapacityCreate,
    *,
    operator_id: int,
    operator_ip: str | None,
    commit: bool = True,
) -> ContractorCapacity:
    data = payload.model_dump(mode="json")
    obj = ContractorCapacity(**data)
    db.add(obj)
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE_CONTRACTOR,
        business_id=obj.id,
        node_code="CONTRACTOR_CAPACITY_CREATE",
        action=ApprovalAction.CREATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        after_snapshot=_contractor_snapshot(obj),
    )
    if commit:
        db.commit()
        db.refresh(obj)
    return obj


def _active_occupied_count(obj: ContractorCapacity) -> int:
    active_statuses = {OperationStatus.WAITING_DISPATCH, OperationStatus.DISPATCHED, OperationStatus.WORKING}
    return sum(1 for sheet in obj.operations if sheet.status in active_statuses)


def _local_status_from_external(team: ExternalContractorTeam, available_count: int) -> ContractorCapacityStatus:
    if team.status in {ContractorCapacityStatus.OFFLINE, ContractorCapacityStatus.EXCEPTION}:
        return team.status
    if available_count <= 0:
        return ContractorCapacityStatus.BUSY
    return team.status


def _mark_missing_external_capacity(obj: ContractorCapacity, *, synced_at: datetime) -> None:
    if _active_occupied_count(obj) > 0:
        obj.sync_status = ContractorCapacitySyncStatus.CONFLICT
        obj.sync_error_message = "外部系统本次未返回该队伍，但本地存在未完成关联工单"
    else:
        obj.sync_status = ContractorCapacitySyncStatus.INVALID
        obj.sync_error_message = "外部系统本次未返回该队伍，已标记失效"
        obj.status = ContractorCapacityStatus.OFFLINE
        obj.available_count = 0
    obj.last_synced_at = synced_at


def _upsert_external_team(
    db: Session,
    team: ExternalContractorTeam,
    *,
    synced_at: datetime,
) -> tuple[ContractorCapacity, str]:
    existing = db.scalar(
        select(ContractorCapacity)
        .options(selectinload(ContractorCapacity.operations))
        .where(
            ContractorCapacity.external_system_id == team.external_system_id,
            ContractorCapacity.report_date == team.report_date,
        )
        .limit(1)
    )
    action = "updated" if existing is not None else "created"
    obj = existing or ContractorCapacity(
        external_system_id=team.external_system_id,
        contractor_name=team.contractor_name,
        team_name=team.team_name,
        report_date=team.report_date,
    )
    if existing is None:
        db.add(obj)

    occupied_count = _active_occupied_count(obj) if existing is not None else 0
    has_local_occupation = occupied_count > 0
    external_unavailable = team.status in {ContractorCapacityStatus.OFFLINE, ContractorCapacityStatus.EXCEPTION} or team.available_count <= 0
    available_count = max(team.available_count - occupied_count, 0)

    obj.contractor_name = team.contractor_name
    obj.team_name = team.team_name
    obj.available_count = available_count
    obj.status = _local_status_from_external(team, available_count)
    obj.capability_tags = team.capability_tags
    obj.external_status = team.external_status
    obj.source_type = ContractorCapacitySourceType.EXTERNAL_SYNC
    obj.last_synced_at = synced_at
    obj.contact_name = team.contact_name
    obj.contact_phone = team.contact_phone
    obj.qualification_expire_at = team.qualification_expire_at
    obj.equipment_summary = team.equipment_summary
    obj.sync_error_message = None

    if has_local_occupation and external_unavailable:
        obj.sync_status = ContractorCapacitySyncStatus.CONFLICT
        obj.sync_error_message = "外部系统显示队伍不可用，但本地存在未完成关联工单"
    else:
        obj.sync_status = ContractorCapacitySyncStatus.PENDING_CONFIRM
    db.flush()
    return obj, action


def sync_contractor_capacities(
    db: Session,
    *,
    report_date: date,
    operator_id: int | None,
    operator_ip: str | None,
    client: ContractorExternalClient | None = None,
    sync_type: ContractorCapacitySyncType = ContractorCapacitySyncType.MANUAL,
    external_system_id: str | None = None,
) -> ContractorCapacitySyncLog:
    started_at = datetime.now(timezone.utc)
    client = client or ContractorExternalClient()
    log = ContractorCapacitySyncLog(
        sync_type=sync_type,
        status=ContractorCapacitySyncResultStatus.SUCCESS,
        started_at=started_at,
        operator_id=operator_id,
        raw_summary={},
    )
    db.add(log)
    db.flush()

    created_count = 0
    updated_count = 0
    ignored_count = 0
    failed_count = 0
    synced_ids: set[int] = set()
    try:
        teams = client.fetch_capacities(report_date=report_date, external_system_id=external_system_id)
        for team in teams:
            try:
                with db.begin_nested():
                    obj, action = _upsert_external_team(db, team, synced_at=started_at)
                synced_ids.add(obj.id)
                if action == "created":
                    created_count += 1
                else:
                    updated_count += 1
            except Exception:
                failed_count += 1

        existing_stmt = (
            select(ContractorCapacity)
            .options(selectinload(ContractorCapacity.operations))
            .where(
                ContractorCapacity.report_date == report_date,
                ContractorCapacity.source_type == ContractorCapacitySourceType.EXTERNAL_SYNC,
            )
        )
        if external_system_id is not None:
            existing_stmt = existing_stmt.where(ContractorCapacity.external_system_id == external_system_id)
        existing_rows = db.scalars(existing_stmt).all()
        for obj in existing_rows:
            if obj.id in synced_ids:
                continue
            _mark_missing_external_capacity(obj, synced_at=started_at)
            ignored_count += 1

        success_count = created_count + updated_count
        log.success_count = success_count
        log.failed_count = failed_count
        log.created_count = created_count
        log.updated_count = updated_count
        log.ignored_count = ignored_count
        log.finished_at = datetime.now(timezone.utc)
        log.status = (
            ContractorCapacitySyncResultStatus.PARTIAL
            if failed_count and success_count
            else ContractorCapacitySyncResultStatus.FAILED
            if failed_count
            else ContractorCapacitySyncResultStatus.SUCCESS
        )
        log.raw_summary = {
            "report_date": report_date.isoformat(),
            "external_system_id": external_system_id,
            "connection_status": client.connection_status,
        }
        write_approval_log(
            db,
            business_type=BUSINESS_TYPE_CONTRACTOR,
            business_id=log.id,
            node_code="CONTRACTOR_CAPACITY_SYNC",
            action=ApprovalAction.UPDATE,
            operator_id=operator_id,
            operator_ip=operator_ip,
            after_snapshot={
                "status": log.status.value,
                "created_count": created_count,
                "updated_count": updated_count,
                "ignored_count": ignored_count,
                "failed_count": failed_count,
            },
        )
        db.commit()
        db.refresh(log)
        return log
    except ContractorExternalClientError as exc:
        log.status = ContractorCapacitySyncResultStatus.FAILED
        log.failed_count = 1
        log.error_message = str(exc)
        log.finished_at = datetime.now(timezone.utc)
        log.raw_summary = {"report_date": report_date.isoformat(), "connection_status": client.connection_status}
        write_approval_log(
            db,
            business_type=BUSINESS_TYPE_CONTRACTOR,
            business_id=log.id,
            node_code="CONTRACTOR_CAPACITY_SYNC_FAILED",
            action=ApprovalAction.UPDATE,
            operator_id=operator_id,
            operator_ip=operator_ip,
            after_snapshot={"status": log.status.value, "error_message": log.error_message},
        )
        db.commit()
        db.refresh(log)
        return log


def list_contractor_sync_logs(db: Session, query: ContractorCapacitySyncLogQuery) -> tuple[list[ContractorCapacitySyncLog], int]:
    stmt = select(ContractorCapacitySyncLog)
    if query.status:
        stmt = stmt.where(ContractorCapacitySyncLog.status == query.status)
    if query.sync_type:
        stmt = stmt.where(ContractorCapacitySyncLog.sync_type == query.sync_type)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ContractorCapacitySyncLog.started_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return list(rows), total


def get_contractor_sync_summary(db: Session) -> dict[str, Any]:
    client = ContractorExternalClient()
    latest = db.scalar(select(ContractorCapacitySyncLog).order_by(ContractorCapacitySyncLog.started_at.desc()).limit(1))
    exception_count = db.scalar(
        select(func.count()).select_from(ContractorCapacity).where(
            ContractorCapacity.sync_status.in_([ContractorCapacitySyncStatus.CONFLICT, ContractorCapacitySyncStatus.INVALID]),
        )
    ) or 0
    return {
        "connection_status": client.connection_status,
        "last_sync_time": latest.finished_at if latest else None,
        "last_sync_status": latest.status if latest else None,
        "created_count": latest.created_count if latest else 0,
        "updated_count": latest.updated_count if latest else 0,
        "ignored_count": latest.ignored_count if latest else 0,
        "failed_count": latest.failed_count if latest else 0,
        "exception_count": exception_count,
    }


def get_contractor_overview(db: Session, *, report_date: date | None = None) -> dict[str, int]:
    stmt = select(ContractorCapacity)
    if report_date:
        stmt = stmt.where(ContractorCapacity.report_date == report_date)
    rows = list(db.scalars(stmt).all())
    return {
        "reported_team_count": len(rows),
        "available_team_count": sum(max(row.available_count, 0) for row in rows),
        "busy_team_count": sum(1 for row in rows if row.status == ContractorCapacityStatus.BUSY),
        "offline_team_count": sum(1 for row in rows if row.status == ContractorCapacityStatus.OFFLINE),
        "sync_exception_count": sum(1 for row in rows if row.sync_status in {ContractorCapacitySyncStatus.CONFLICT, ContractorCapacitySyncStatus.INVALID}),
        "major_repair_team_count": sum(1 for row in rows if bool((row.capability_tags or {}).get("major_repair"))),
    }


def confirm_contractor_capacity(
    db: Session,
    contractor_id: int,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> ContractorCapacity:
    obj = get_contractor_capacity(db, contractor_id)
    before = _contractor_snapshot(obj)
    obj.sync_status = ContractorCapacitySyncStatus.SYNCED
    obj.confirmed_at = datetime.now(timezone.utc)
    obj.confirmed_by_id = operator_id
    obj.sync_error_message = None
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE_CONTRACTOR,
        business_id=obj.id,
        node_code="CONTRACTOR_CAPACITY_CONFIRM",
        action=ApprovalAction.APPROVE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        before_snapshot=before,
        after_snapshot=_contractor_snapshot(obj),
    )
    db.commit()
    db.refresh(obj)
    return obj


def mark_contractor_exception(
    db: Session,
    contractor_id: int,
    *,
    reason: str,
    operator_id: int,
    operator_ip: str | None,
) -> ContractorCapacity:
    obj = get_contractor_capacity(db, contractor_id)
    before = _contractor_snapshot(obj)
    obj.status = ContractorCapacityStatus.EXCEPTION
    obj.source_type = ContractorCapacitySourceType.SYNC_ERROR
    obj.sync_status = ContractorCapacitySyncStatus.CONFLICT
    obj.sync_error_message = reason
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE_CONTRACTOR,
        business_id=obj.id,
        node_code="CONTRACTOR_CAPACITY_EXCEPTION",
        action=ApprovalAction.UPDATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        comment=reason,
        before_snapshot=before,
        after_snapshot=_contractor_snapshot(obj),
    )
    db.commit()
    db.refresh(obj)
    return obj


def resolve_contractor_exception(
    db: Session,
    contractor_id: int,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> ContractorCapacity:
    obj = get_contractor_capacity(db, contractor_id)
    before = _contractor_snapshot(obj)
    obj.sync_status = ContractorCapacitySyncStatus.PENDING_CONFIRM
    obj.sync_error_message = None
    if obj.status == ContractorCapacityStatus.EXCEPTION:
        obj.status = ContractorCapacityStatus.AVAILABLE if obj.available_count > 0 else ContractorCapacityStatus.BUSY
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE_CONTRACTOR,
        business_id=obj.id,
        node_code="CONTRACTOR_CAPACITY_EXCEPTION_RESOLVE",
        action=ApprovalAction.UPDATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        before_snapshot=before,
        after_snapshot=_contractor_snapshot(obj),
    )
    db.commit()
    db.refresh(obj)
    return obj


def list_contractor_operation_sheets(db: Session, contractor_id: int) -> list[dict[str, Any]]:
    get_contractor_capacity(db, contractor_id)
    rows = db.scalars(
        select(WorkoverOperationSheet)
        .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
        .options(selectinload(WorkoverOperationSheet.project))
        .where(WorkoverOperationSheet.contractor_capacity_id == contractor_id)
        .order_by(WorkoverOperationSheet.created_at.desc())
    ).all()
    return [
        {
            "id": row.id,
            "operation_no": row.operation_no,
            "status": row.status,
            "well_no": row.project.well_no if row.project else None,
            "dispatch_time": row.last_a5_sync_at,
            "a5_status": row.a5_status,
            "created_at": row.created_at,
        }
        for row in rows
    ]


def update_contractor_capacity(
    db: Session,
    contractor_id: int,
    payload: ContractorCapacityUpdate,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> ContractorCapacity:
    obj = get_contractor_capacity(db, contractor_id)
    before = _contractor_snapshot(obj)
    data = payload.model_dump(mode="json", exclude_unset=True)
    for key, value in data.items():
        setattr(obj, key, value)
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE_CONTRACTOR,
        business_id=obj.id,
        node_code="CONTRACTOR_CAPACITY_UPDATE",
        action=ApprovalAction.UPDATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        before_snapshot=before,
        after_snapshot=_contractor_snapshot(obj),
    )
    db.commit()
    db.refresh(obj)
    return obj


def list_operation_sheets(db: Session, query: WorkoverOperationSheetQuery) -> tuple[list[WorkoverOperationSheet], int]:
    base_stmt = _apply_sheet_filters(
        select(WorkoverOperationSheet)
        .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
        .outerjoin(ContractorCapacity, WorkoverOperationSheet.contractor_capacity_id == ContractorCapacity.id)
        .options(
            selectinload(WorkoverOperationSheet.project),
            selectinload(WorkoverOperationSheet.contractor_capacity),
        ),
        query,
    )
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    rows = db.scalars(
        base_stmt.order_by(WorkoverOperationSheet.created_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return list(rows), total


def get_operation_sheet(db: Session, sheet_id: int) -> WorkoverOperationSheet:
    obj = db.get(WorkoverOperationSheet, sheet_id)
    if obj is None:
        raise BusinessException(BAD_REQUEST, "修井运行表记录不存在")
    return obj


def _new_operation_no() -> str:
    return f"OP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"


def ensure_operation_sheet_for_project(
    db: Session,
    project: WorkoverProjectPool,
    *,
    operator_id: int | None = None,
    operator_ip: str | None = None,
) -> WorkoverOperationSheet:
    existing = db.scalar(
        select(WorkoverOperationSheet)
        .where(WorkoverOperationSheet.project_id == project.id)
        .limit(1)
    )
    if existing is not None:
        if (
            project.status == ProjectPoolStatus.APPROVED
            and existing.status in {OperationStatus.DISPATCHED, OperationStatus.WORKING, OperationStatus.FINISHED}
        ):
            project.status = ProjectPoolStatus.DISPATCHED
            db.flush()
        return existing
    if project.status != ProjectPoolStatus.APPROVED:
        raise BusinessException(CONFLICT, f"项目 {project.well_no} 尚未入运行库，不能创建运行表")

    sheet = WorkoverOperationSheet(
        project_id=project.id,
        operation_no=_new_operation_no(),
        status=OperationStatus.WAITING_DISPATCH,
    )
    db.add(sheet)
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE_OPERATION,
        business_id=sheet.id,
        node_code="OPERATION_SHEET_AUTO_CREATE",
        action=ApprovalAction.CREATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        after_snapshot=_sheet_snapshot(sheet),
    )
    return sheet


def sync_approved_projects_to_operation_sheets(
    db: Session,
    *,
    operator_id: int | None = None,
    operator_ip: str | None = None,
) -> list[WorkoverOperationSheet]:
    approved_projects = db.scalars(
        select(WorkoverProjectPool)
        .where(
            WorkoverProjectPool.status == ProjectPoolStatus.APPROVED,
            WorkoverProjectPool.is_deleted.is_(False),
        )
    ).all()
    sheets: list[WorkoverOperationSheet] = []
    for project in approved_projects:
        sheet = ensure_operation_sheet_for_project(
            db,
            project,
            operator_id=operator_id,
            operator_ip=operator_ip,
        )
        sheets.append(sheet)
    db.commit()
    for sheet in sheets:
        db.refresh(sheet)
    return sheets


def create_operation_sheet(
    db: Session,
    payload: WorkoverOperationSheetCreate,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> WorkoverOperationSheet:
    data = payload.model_dump(mode="json")
    project = db.get(WorkoverProjectPool, payload.project_id)
    if project is None or project.is_deleted:
        raise BusinessException(BAD_REQUEST, "上修项目池记录不存在")
    if project.status != ProjectPoolStatus.APPROVED:
        raise BusinessException(CONFLICT, "只有已入库项目才能创建修井运行表")
    existing = db.scalar(
        select(WorkoverOperationSheet)
        .where(WorkoverOperationSheet.project_id == payload.project_id)
        .limit(1)
    )
    if existing is not None:
        return existing
    operation_no = _new_operation_no()
    obj = WorkoverOperationSheet(
        **data,
        operation_no=operation_no,
        status=OperationStatus.WAITING_DISPATCH,
    )
    db.add(obj)
    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE_OPERATION,
        business_id=obj.id,
        node_code="OPERATION_SHEET_CREATE",
        action=ApprovalAction.CREATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        after_snapshot=_sheet_snapshot(obj),
    )
    db.commit()
    db.refresh(obj)
    return obj


def acquire_dispatch_lock(contractor_capacity_id: int) -> bool:
    """获取 Redis 分布式派工锁，防止并发派工冲突。"""
    lock_key = f"{LOCK_PREFIX}{contractor_capacity_id}"
    return cache_client.set_json(
        lock_key,
        {"locked_at": datetime.now(timezone.utc).isoformat()},
        expire_seconds=LOCK_TTL,
        nx=True,
    )


def release_dispatch_lock(contractor_capacity_id: int) -> None:
    """释放 Redis 分布式派工锁。"""
    lock_key = f"{LOCK_PREFIX}{contractor_capacity_id}"
    cache_client.delete(lock_key)


def dispatch_operation(
    db: Session,
    sheet_id: int,
    contractor_capacity_id: int,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> WorkoverOperationSheet:
    """分配上修队伍并发起 A5 措施审核办理，含 Redis 分布式锁防重机制。"""
    # 1. 获取分布式锁
    if not acquire_dispatch_lock(contractor_capacity_id):
        raise BusinessException(CONFLICT, "该队伍正在被其他调度员操作，请稍后重试")

    try:
        # 2. 获取工单
        sheet = get_operation_sheet(db, sheet_id)
        if sheet.status != OperationStatus.WAITING_DISPATCH:
            raise BusinessException(CONFLICT, f"工单 {sheet.operation_no} 当前状态不允许派工")
        if sheet.contractor_capacity_id is not None:
            raise BusinessException(CONFLICT, f"工单 {sheet.operation_no} 已分配队伍，等待 A5 审核下发")

        # 3. 检查承包商状态
        contractor = get_contractor_capacity(db, contractor_capacity_id)
        if contractor.status != ContractorCapacityStatus.AVAILABLE:
            raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 当前状态不可用")
        if contractor.sync_status in {ContractorCapacitySyncStatus.CONFLICT, ContractorCapacitySyncStatus.INVALID}:
            raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 存在同步异常，确认处理后才能派工")
        if contractor.available_count <= 0:
            raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 今日可用队伍数不足")

        # 4. 仅完成本地队伍分配，A5 审核/下发回写后再推进本地作业状态
        before = _sheet_snapshot(sheet)
        sheet.contractor_capacity_id = contractor_capacity_id
        sheet.a5_status = "待A5措施审核"
        sheet.a5_remark = "已分配上修队伍，等待进入A5完成措施审核及下发"
        sheet.last_a5_sync_at = datetime.now(timezone.utc)
        detail = dict(sheet.progress_detail or {})
        detail["dispatch"] = {
            "source": "local_dispatch",
            "contractor_capacity_id": contractor_capacity_id,
            "contractor_name": contractor.contractor_name,
            "team_name": contractor.team_name,
            "a5_next_step": "measure_review",
            "updated_at": sheet.last_a5_sync_at.isoformat(),
        }
        sheet.progress_detail = detail
        db.flush()

        # 5. 按日报可用队伍数扣减，剩余为 0 时才标记忙碌
        contractor.available_count -= 1
        if contractor.available_count == 0:
            contractor.status = ContractorCapacityStatus.BUSY
        db.flush()

        # 6. 写审计日志
        write_approval_log(
            db,
            business_type=BUSINESS_TYPE_OPERATION,
            business_id=sheet.id,
            node_code="ASSIGN_AND_A5_REVIEW",
            action=ApprovalAction.APPROVE,
            operator_id=operator_id,
            operator_ip=operator_ip,
            before_snapshot=before,
            after_snapshot=_sheet_snapshot(sheet),
        )
        db.commit()
        db.refresh(sheet)
        return sheet

    except Exception:
        db.rollback()
        raise
    finally:
        release_dispatch_lock(contractor_capacity_id)


def update_sheet_progress(
    db: Session,
    sheet_id: int,
    payload: ProgressPatch,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> WorkoverOperationSheet:
    sheet = get_operation_sheet(db, sheet_id)
    before = _sheet_snapshot(sheet)
    sheet.progress = payload.progress
    detail = dict(sheet.progress_detail or {})
    detail.update(payload.progress_detail or {})
    sheet.progress_detail = detail
    now = datetime.now(timezone.utc)

    if 0 < payload.progress < 100 and sheet.status == OperationStatus.DISPATCHED:
        sheet.status = OperationStatus.WORKING
        sheet.actual_start_at = sheet.actual_start_at or now
    elif payload.progress == 100 and sheet.status in {OperationStatus.DISPATCHED, OperationStatus.WORKING}:
        sheet.status = OperationStatus.FINISHED
        sheet.actual_start_at = sheet.actual_start_at or now
        sheet.actual_end_at = now
        if sheet.contractor_capacity is not None:
            sheet.contractor_capacity.available_count += 1
            sheet.contractor_capacity.status = ContractorCapacityStatus.AVAILABLE

    db.flush()
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE_OPERATION,
        business_id=sheet.id,
        node_code="PROGRESS_UPDATE",
        action=ApprovalAction.UPDATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        before_snapshot=before,
        after_snapshot=_sheet_snapshot(sheet),
    )
    db.commit()
    db.refresh(sheet)
    return sheet


def select_priority_sheets(db: Session) -> list[WorkoverOperationSheet]:
    """查询待派工工单，按审批通过时间升序+产量优先级降序排列。"""
    stmt = (
        select(WorkoverOperationSheet)
        .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
        .where(
            WorkoverOperationSheet.status == OperationStatus.WAITING_DISPATCH,
            WorkoverOperationSheet.contractor_capacity_id.is_(None),
        )
        .order_by(
            WorkoverProjectPool.approved_at.asc().nullslast(),
            WorkoverProjectPool.production_priority.desc(),
        )
    )
    return list(db.scalars(stmt).all())


def get_operation_analytics(db: Session) -> dict[str, Any]:
    """修井运行基础统计。

    统计内容：运行状态分布、派工情况、队伍工作量、措施类型分布、近30天趋势。
    """
    sheets = list(db.scalars(select(WorkoverOperationSheet)).all())

    total = len(sheets)
    status_counts = {}
    team_workload: dict[str, int] = {}
    measure_type_counts: dict[str, int] = {}

    for sheet in sheets:
        status_counts[sheet.status.value] = status_counts.get(sheet.status.value, 0) + 1

        if sheet.contractor_capacity and sheet.contractor_capacity.team_name:
            team = sheet.contractor_capacity.team_name
            team_workload[team] = team_workload.get(team, 0) + 1

        if sheet.project and sheet.project.measures_jsonb:
            measures = sheet.project.measures_jsonb.get("measures", [])
            if isinstance(measures, list):
                for m in measures:
                    mt = m.get("measure_type", "") if isinstance(m, dict) else ""
                    if mt:
                        measure_type_counts[mt] = measure_type_counts.get(mt, 0) + 1

    dispatched = status_counts.get("DISPATCHED", 0)
    working = status_counts.get("WORKING", 0)
    finished = status_counts.get("FINISHED", 0)
    waiting = status_counts.get("WAITING_DISPATCH", 0)
    canceled = status_counts.get("CANCELED", 0)

    dispatch_rate = round((dispatched + working + finished) / total * 100, 1) if total > 0 else 0
    completion_rate = round(finished / total * 100, 1) if total > 0 else 0

    return {
        "total_sheets": total,
        "status_distribution": {
            "waiting_dispatch": waiting,
            "dispatched": dispatched,
            "working": working,
            "finished": finished,
            "canceled": canceled,
        },
        "dispatch_rate": dispatch_rate,
        "completion_rate": completion_rate,
        "team_workload": sorted(
            [{"team_name": k, "sheet_count": v} for k, v in team_workload.items()],
            key=lambda x: -x["sheet_count"],
        ),
        "measure_type_distribution": sorted(
            [{"measure_type": k, "count": v} for k, v in measure_type_counts.items()],
            key=lambda x: -x["count"],
        ),
        "anomaly_count": 0,
    }
