import uuid
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from typing import Any

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessException
from app.core.redis import cache_client
from app.core.status_codes import BAD_REQUEST, CONFLICT, FORBIDDEN
from app.models.approval import ApprovalAction
from app.models.rbac import User
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
from app.services.data_scope_service import (
    apply_contractor_capacity_read_scope,
    apply_workover_operation_scope,
    can_manage_contractor_capacity,
)
from app.services.dictionary_service import ensure_dictionary_values
from app.services.contractor_external_client import ContractorExternalClient, ContractorExternalClientError, ExternalContractorTeam

BUSINESS_TYPE_CONTRACTOR = "contractor_capacity"
BUSINESS_TYPE_OPERATION = "workover_operation_sheet"

LOCK_PREFIX = "dispatch:lock:"
LOCK_TTL = 30  # seconds
ACTIVE_OPERATION_STATUSES = {OperationStatus.PENDING_A5, OperationStatus.DISPATCHED, OperationStatus.WORKING}
BUSINESS_TZ = ZoneInfo("Asia/Shanghai")
CAPABILITY_ALIASES = {
    "major_workover": "major_repair", "pump_repair": "major_repair", "pump_inspection": "major_repair",
    "sand_washing": "sand_control", "tubing_replacement": "major_repair", "casing_damage_treatment": "major_repair",
}
CONTRACTOR_CREATE_UPSERT_FIELDS = {
    "available_count",
    "status",
    "capability_tags",
    "external_system_id",
    "external_status",
    "source_type",
    "sync_status",
    "contact_name",
    "contact_phone",
    "qualification_expire_at",
    "equipment_summary",
    # A re-submitted local supplement is a new operator declaration.  Keep its
    # explanation in sync with the latest declaration instead of displaying a
    # stale exception reason from a previous submission.
    "sync_error_message",
}


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
        "created_by_id": obj.created_by_id,
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
        "a5_status": obj.a5_status,
        "a5_sync_result": obj.a5_sync_result,
        "last_a5_report_date": obj.last_a5_report_date.isoformat() if obj.last_a5_report_date else None,
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
    effective_start = func.coalesce(
        WorkoverOperationSheet.actual_start_at,
        WorkoverOperationSheet.planned_start_at,
    )
    effective_end = func.coalesce(
        WorkoverOperationSheet.actual_end_at,
        WorkoverOperationSheet.planned_end_at,
    )
    if query.start_date:
        start_at = datetime.combine(query.start_date, time.min)
        stmt = stmt.where(or_(effective_end.is_(None), effective_end >= start_at))
    if query.end_date:
        end_at = datetime.combine(query.end_date, time.max)
        stmt = stmt.where(effective_start <= end_at)
    return stmt


def _occupied_count_subquery():
    return (
        select(
            WorkoverOperationSheet.contractor_capacity_id.label("contractor_capacity_id"),
            func.count(WorkoverOperationSheet.id).label("occupied_count"),
        )
        .where(
            WorkoverOperationSheet.contractor_capacity_id.is_not(None),
            WorkoverOperationSheet.status.in_(ACTIVE_OPERATION_STATUSES),
        )
        .group_by(WorkoverOperationSheet.contractor_capacity_id)
        .subquery()
    )


def list_contractor_capacities(db: Session, query: ContractorCapacityQuery, *, current_user: User | None = None) -> tuple[list[ContractorCapacity], int]:
    base_stmt = _apply_contractor_filters(select(ContractorCapacity), query)
    if current_user is not None:
        base_stmt = apply_contractor_capacity_read_scope(base_stmt, current_user)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    occupied_counts = _occupied_count_subquery()
    rows = db.execute(
        base_stmt
        .outerjoin(occupied_counts, ContractorCapacity.id == occupied_counts.c.contractor_capacity_id)
        .add_columns(func.coalesce(occupied_counts.c.occupied_count, 0))
        .order_by(ContractorCapacity.report_date.desc(), ContractorCapacity.created_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    items: list[ContractorCapacity] = []
    for obj, occupied_count in rows:
        obj._occupied_count = occupied_count
        items.append(obj)
    return items, total


def get_contractor_capacity(db: Session, contractor_id: int) -> ContractorCapacity:
    obj = db.get(ContractorCapacity, contractor_id)
    if obj is None:
        raise BusinessException(BAD_REQUEST, "承包商运力记录不存在")
    return obj


def get_contractor_capacity_for_user(db: Session, contractor_id: int, user: User, *, require_manage: bool = False) -> ContractorCapacity:
    obj = get_contractor_capacity(db, contractor_id)
    if require_manage:
        allowed = can_manage_contractor_capacity(user, obj)
    else:
        scoped = apply_contractor_capacity_read_scope(
            select(ContractorCapacity.id).where(ContractorCapacity.id == contractor_id),
            user,
        )
        allowed = db.scalar(scoped.limit(1)) is not None
    if not allowed:
        raise BusinessException(FORBIDDEN, "无权访问该承包商运力记录")
    return obj


def create_contractor_capacity(
    db: Session,
    payload: ContractorCapacityCreate,
    *,
    operator_id: int,
    operator_ip: str | None,
    current_user: User | None = None,
    commit: bool = True,
) -> ContractorCapacity:
    data = payload.model_dump()
    # Provenance and confirmation are server-owned for locally supplemented data.
    data.update({
        "external_system_id": None,
        "external_status": None,
        "source_type": ContractorCapacitySourceType.LOCAL_SUPPLEMENT,
        "sync_status": ContractorCapacitySyncStatus.PENDING_CONFIRM,
    })
    existing = db.scalar(
        select(ContractorCapacity)
        .where(
            ContractorCapacity.contractor_name == payload.contractor_name,
            ContractorCapacity.team_name == payload.team_name,
            ContractorCapacity.report_date == payload.report_date,
        )
        .limit(1)
    )
    if (
        existing is not None
        and existing.source_type == ContractorCapacitySourceType.EXTERNAL_SYNC
        and existing.sync_status not in {ContractorCapacitySyncStatus.CONFLICT, ContractorCapacitySyncStatus.INVALID}
    ):
        raise BusinessException(CONFLICT, "同日同队伍已存在外部同步运力，请在同步确认流程中处理")
    if existing is not None:
        if current_user is not None:
            if not can_manage_contractor_capacity(current_user, existing):
                raise BusinessException(FORBIDDEN, "无权覆盖其他用户的同日同队伍报备")
        elif existing.created_by_id is not None and existing.created_by_id != operator_id:
            raise BusinessException(FORBIDDEN, "无权覆盖其他用户的同日同队伍报备")

    obj = existing or ContractorCapacity(
        contractor_name=payload.contractor_name,
        team_name=payload.team_name,
        report_date=payload.report_date,
        created_by_id=operator_id,
    )
    before = _contractor_snapshot(obj) if existing is not None else None
    if existing is None:
        db.add(obj)
    for key, value in data.items():
        if existing is None or key in CONTRACTOR_CREATE_UPSERT_FIELDS:
            setattr(obj, key, value)
    if existing is not None:
        obj.created_by_id = operator_id
        obj.sync_status = ContractorCapacitySyncStatus.PENDING_CONFIRM
        obj.confirmed_at = None
        obj.confirmed_by_id = None
    else:
        obj.source_type = ContractorCapacitySourceType.LOCAL_SUPPLEMENT
        obj.sync_status = ContractorCapacitySyncStatus.PENDING_CONFIRM
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessException(CONFLICT, "同日同队伍运力已存在，请刷新后修改现有报备") from exc
    write_approval_log(
        db,
        business_type=BUSINESS_TYPE_CONTRACTOR,
        business_id=obj.id,
        node_code="CONTRACTOR_CAPACITY_CREATE" if existing is None else "CONTRACTOR_CAPACITY_REDECLARE",
        action=ApprovalAction.CREATE if existing is None else ApprovalAction.UPDATE,
        operator_id=operator_id,
        operator_ip=operator_ip,
        before_snapshot=before,
        after_snapshot=_contractor_snapshot(obj),
    )
    if commit:
        db.commit()
        db.refresh(obj)
    return obj


def _active_occupied_count(obj: ContractorCapacity) -> int:
    return sum(1 for sheet in obj.operations if sheet.status in ACTIVE_OPERATION_STATUSES)


def _local_status_from_external(team: ExternalContractorTeam, available_count: int) -> ContractorCapacityStatus:
    if team.status in {ContractorCapacityStatus.OFFLINE, ContractorCapacityStatus.EXCEPTION}:
        return team.status
    if available_count <= 0:
        return ContractorCapacityStatus.BUSY
    return ContractorCapacityStatus.AVAILABLE


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


def _mark_missing_local_capacity(obj: ContractorCapacity, *, synced_at: datetime) -> None:
    if _active_occupied_count(obj) > 0:
        obj.sync_status = ContractorCapacitySyncStatus.CONFLICT
        obj.sync_error_message = "外部系统本次未返回该本地补录队伍，但本地存在未完成关联工单"
    else:
        obj.sync_status = ContractorCapacitySyncStatus.INVALID
        obj.sync_error_message = "外部系统本次未返回该本地补录队伍，已标记失效"
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
    if existing is None:
        existing = db.scalar(
            select(ContractorCapacity)
            .options(selectinload(ContractorCapacity.operations))
            .where(
                ContractorCapacity.contractor_name == team.contractor_name,
                ContractorCapacity.team_name == team.team_name,
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
    # The external snapshot is total capacity; keep locally occupied sheets
    # deducted until they have reached a terminal state.
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


def _sync_contractor_capacities_locked(
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
    synced_external_ids: set[str] = set()
    synced_team_keys: set[tuple[str, str]] = set()
    failed_teams: list[dict[str, str]] = []
    try:
        try:
            teams = client.fetch_capacities(report_date=report_date, external_system_id=external_system_id)
        except ContractorExternalClientError:
            raise
        except Exception as exc:
            raise ContractorExternalClientError(f"外部承包商系统调用异常：{exc}") from exc
        invalid_rows = list(getattr(client, "invalid_rows", []) or [])
        failed_count += len(invalid_rows)
        failed_teams.extend(invalid_rows)
        if not teams and external_system_id is None:
            raise ContractorExternalClientError("外部承包商系统返回空响应或无有效运力数据，已保留本地日快照")
        for team in teams:
            # A returned record must never be treated as externally deleted merely because
            # its local upsert failed.
            synced_external_ids.add(team.external_system_id)
            synced_team_keys.add((team.contractor_name, team.team_name))
            capacity_id = db.scalar(
                select(ContractorCapacity.id).where(
                    ContractorCapacity.external_system_id == team.external_system_id,
                    ContractorCapacity.report_date == team.report_date,
                )
            )
            capacity_lock: str | None = acquire_dispatch_lock(capacity_id) if capacity_id is not None else None
            if capacity_id is not None and not capacity_lock:
                failed_count += 1
                failed_teams.append({"external_system_id": team.external_system_id, "contractor_name": team.contractor_name, "team_name": team.team_name, "error": "队伍正在被派工操作"})
                continue
            try:
                with db.begin_nested():
                    obj, action = _upsert_external_team(db, team, synced_at=started_at)
                synced_ids.add(obj.id)
                if action == "created":
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as exc:
                failed_count += 1
                failed_teams.append({
                    "external_system_id": team.external_system_id,
                    "contractor_name": team.contractor_name,
                    "team_name": team.team_name,
                    "error": str(exc),
                })
            finally:
                if capacity_id is not None:
                    release_dispatch_lock(capacity_id, capacity_lock)

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
        missing_reconciliation_skipped = bool(invalid_rows)
        if not missing_reconciliation_skipped:
            existing_rows = db.scalars(existing_stmt).all()
            for obj in existing_rows:
                if obj.id in synced_ids or (
                    obj.external_system_id is not None and obj.external_system_id in synced_external_ids
                ) or (obj.contractor_name, obj.team_name) in synced_team_keys:
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
            "failed_teams": failed_teams,
            "missing_reconciliation_skipped": missing_reconciliation_skipped,
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
    except Exception:
        db.rollback()
        raise


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
    """Serialize a daily snapshot sync across API workers and schedulers."""
    lock_key = f"contractor:capacity-sync:{report_date.isoformat()}"
    lock_value = {"token": uuid.uuid4().hex}
    if not cache_client.set_lock_json(lock_key, lock_value, expire_seconds=900, nx=True):
        raise BusinessException(CONFLICT, "该日期的运力同步正在执行，请勿重复触发")
    try:
        return _sync_contractor_capacities_locked(
            db,
            report_date=report_date,
            operator_id=operator_id,
            operator_ip=operator_ip,
            client=client,
            sync_type=sync_type,
            external_system_id=external_system_id,
        )
    finally:
        cache_client.delete_json_if_matches(lock_key, lock_value)


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


def get_contractor_overview(db: Session, *, report_date: date | None = None, current_user: User | None = None) -> dict[str, int]:
    filters = []
    if report_date:
        filters.append(ContractorCapacity.report_date == report_date)
    stmt = select(
        func.count(ContractorCapacity.id),
        func.coalesce(
            func.sum(case((ContractorCapacity.status == ContractorCapacityStatus.AVAILABLE, ContractorCapacity.available_count), else_=0)),
            0,
        ),
        func.coalesce(func.sum(case((ContractorCapacity.status == ContractorCapacityStatus.BUSY, 1), else_=0)), 0),
        func.coalesce(func.sum(case((ContractorCapacity.status == ContractorCapacityStatus.OFFLINE, 1), else_=0)), 0),
        func.coalesce(
            func.sum(
                case(
                    (
                        ContractorCapacity.sync_status.in_(
                            [ContractorCapacitySyncStatus.CONFLICT, ContractorCapacitySyncStatus.INVALID]
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ),
        func.coalesce(
            func.sum(case((ContractorCapacity.capability_tags["major_repair"].as_boolean().is_(True), 1), else_=0)),
            0,
        ),
    )
    if filters:
        stmt = stmt.where(*filters)
    if current_user is not None:
        stmt = apply_contractor_capacity_read_scope(stmt, current_user)
    row = db.execute(stmt).one()
    return {
        "reported_team_count": int(row[0] or 0),
        "available_team_count": int(row[1] or 0),
        "busy_team_count": int(row[2] or 0),
        "offline_team_count": int(row[3] or 0),
        "sync_exception_count": int(row[4] or 0),
        "major_repair_team_count": int(row[5] or 0),
    }


def confirm_contractor_capacity(
    db: Session,
    contractor_id: int,
    *,
    operator_id: int,
    operator_ip: str | None,
    current_user: User | None = None,
) -> ContractorCapacity:
    obj = _get_contractor_capacity_for_update(db, contractor_id, current_user)
    if obj.sync_status != ContractorCapacitySyncStatus.PENDING_CONFIRM:
        raise BusinessException(CONFLICT, "仅待确认的正常运力可以确认")
    if obj.status in {ContractorCapacityStatus.OFFLINE, ContractorCapacityStatus.EXCEPTION}:
        raise BusinessException(CONFLICT, "离线或异常运力不能确认")
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
    current_user: User | None = None,
) -> ContractorCapacity:
    obj = _get_contractor_capacity_for_update(db, contractor_id, current_user)
    before = _contractor_snapshot(obj)
    obj.status = ContractorCapacityStatus.EXCEPTION
    # Exception is operational state, not provenance; retain external/local source
    # so later missing-record reconciliation continues to include this capacity.
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
    current_user: User | None = None,
) -> ContractorCapacity:
    obj = _get_contractor_capacity_for_update(db, contractor_id, current_user)
    before = _contractor_snapshot(obj)
    obj.sync_status = ContractorCapacitySyncStatus.PENDING_CONFIRM
    obj.sync_error_message = None
    if obj.status == ContractorCapacityStatus.EXCEPTION:
        external_status = (obj.external_status or "").upper()
        if external_status in {"OFFLINE", "EXCEPTION"}:
            obj.status = ContractorCapacityStatus(external_status)
        else:
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


def list_contractor_operation_sheets(db: Session, contractor_id: int, *, current_user: User | None = None) -> list[dict[str, Any]]:
    if current_user is not None:
        get_contractor_capacity_for_user(db, contractor_id, current_user)
    else:
        get_contractor_capacity(db, contractor_id)
    stmt = (
        select(WorkoverOperationSheet)
        .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
        .options(selectinload(WorkoverOperationSheet.project))
        .where(WorkoverOperationSheet.contractor_capacity_id == contractor_id)
        .order_by(WorkoverOperationSheet.created_at.desc())
    )
    if current_user is not None:
        stmt = apply_workover_operation_scope(stmt, current_user)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": row.id,
            "operation_no": row.operation_no,
            "status": row.status,
            "well_no": row.project.well_no if row.project else None,
            "dispatch_time": row.dispatched_at,
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
    current_user: User | None = None,
) -> ContractorCapacity:
    obj = _get_contractor_capacity_for_update(db, contractor_id, current_user)
    before = _contractor_snapshot(obj)
    data = payload.model_dump(exclude_unset=True)
    identity_fields = {"contractor_name", "team_name", "report_date", "capability_tags"}
    if data.keys() & identity_fields and _active_occupied_count(obj) > 0:
        raise BusinessException(CONFLICT, "存在施工中或已派工工单时，不允许修改队伍身份、报备日期或能力标签")
    for key, value in data.items():
        setattr(obj, key, value)
    if data:
        obj.sync_status = ContractorCapacitySyncStatus.PENDING_CONFIRM
        obj.confirmed_at = None
        obj.confirmed_by_id = None
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessException(CONFLICT, "修改后与同日报备队伍重复") from exc
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


def _release_contractor_capacity(contractor: ContractorCapacity) -> None:
    contractor.available_count += 1
    if contractor.status not in {ContractorCapacityStatus.OFFLINE, ContractorCapacityStatus.EXCEPTION}:
        contractor.status = ContractorCapacityStatus.AVAILABLE


def list_operation_sheets(
    db: Session,
    query: WorkoverOperationSheetQuery,
    *,
    current_user: User | None = None,
) -> tuple[list[WorkoverOperationSheet], int]:
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
    if current_user is not None:
        base_stmt = apply_workover_operation_scope(base_stmt, current_user)
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


def get_operation_sheet_for_user(db: Session, sheet_id: int, current_user: User) -> WorkoverOperationSheet:
    stmt = (
        select(WorkoverOperationSheet)
        .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
        .options(
            selectinload(WorkoverOperationSheet.project),
            selectinload(WorkoverOperationSheet.contractor_capacity),
        )
        .where(WorkoverOperationSheet.id == sheet_id)
    )
    obj = db.scalar(apply_workover_operation_scope(stmt, current_user))
    if obj is None:
        raise BusinessException(FORBIDDEN, "无权访问该修井运行表")
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
            and existing.status in {OperationStatus.PENDING_A5, OperationStatus.DISPATCHED, OperationStatus.WORKING, OperationStatus.FINISHED}
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
    try:
        with db.begin_nested():
            db.add(sheet)
            db.flush()
    except IntegrityError:
        # A concurrent creator won the project-level unique constraint.
        existing = db.scalar(
            select(WorkoverOperationSheet).where(WorkoverOperationSheet.project_id == project.id).limit(1)
        )
        if existing is not None:
            return existing
        raise
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
    current_user: User | None = None,
) -> WorkoverOperationSheet:
    data = payload.model_dump(mode="json")
    project_stmt = select(WorkoverProjectPool).where(WorkoverProjectPool.id == payload.project_id)
    if current_user is not None:
        project_stmt = apply_workover_operation_scope(project_stmt, current_user)
    project = db.scalar(project_stmt)
    if project is None or project.is_deleted:
        raise BusinessException(FORBIDDEN if current_user is not None else BAD_REQUEST, "无权访问该上修项目池记录" if current_user is not None else "上修项目池记录不存在")
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
    try:
        with db.begin_nested():
            db.add(obj)
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(WorkoverOperationSheet).where(WorkoverOperationSheet.project_id == payload.project_id).limit(1)
        )
        if existing is not None:
            return existing
        raise
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


def _dispatch_lock_key(resource: str, resource_id: int) -> str:
    return f"{LOCK_PREFIX}{resource}:{resource_id}"


def _acquire_lock(resource: str, resource_id: int) -> str | None:
    if not getattr(cache_client, "distributed_lock_available", True):
        raise BusinessException(CONFLICT, "Redis 不可用，无法安全执行并发敏感操作")
    token = uuid.uuid4().hex
    set_lock = getattr(cache_client, "set_lock_json", cache_client.set_json)
    if set_lock(
        _dispatch_lock_key(resource, resource_id),
        {"token": token, "locked_at": datetime.now(timezone.utc).isoformat()},
        expire_seconds=LOCK_TTL,
        nx=True,
    ):
        return token
    return None


def _release_lock(resource: str, resource_id: int, token: str | bool | None) -> None:
    if not token:
        return
    key = _dispatch_lock_key(resource, resource_id)
    # bool is retained solely for legacy test doubles which return True from acquire.
    if isinstance(token, bool):
        cache_client.delete(key)
        return
    current = cache_client.get_json(key)
    if isinstance(current, dict) and current.get("token") == token:
        cache_client.delete_json_if_matches(key, current)


def acquire_dispatch_lock(contractor_capacity_id: int) -> str | None:
    """Acquire a capacity lock and return its ownership token."""
    return _acquire_lock("capacity", contractor_capacity_id)


def release_dispatch_lock(contractor_capacity_id: int, token: str | bool | None = None) -> None:
    """Release a capacity lock only if its token still owns it."""
    _release_lock("capacity", contractor_capacity_id, token)


def acquire_operation_lock(sheet_id: int) -> str | None:
    return _acquire_lock("operation", sheet_id)


def release_operation_lock(sheet_id: int, token: str | bool | None = None) -> None:
    _release_lock("operation", sheet_id, token)


def _get_operation_sheet_for_update(
    db: Session, sheet_id: int, current_user: User | None = None
) -> WorkoverOperationSheet:
    stmt = (
        select(WorkoverOperationSheet)
        .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
        .options(selectinload(WorkoverOperationSheet.project), selectinload(WorkoverOperationSheet.contractor_capacity))
        .where(WorkoverOperationSheet.id == sheet_id)
        .with_for_update()
    )
    if current_user is not None:
        stmt = apply_workover_operation_scope(stmt, current_user)
    obj = db.scalar(stmt)
    if obj is None:
        raise BusinessException(FORBIDDEN if current_user is not None else BAD_REQUEST, "无权访问该修井运行表" if current_user is not None else "修井运行表记录不存在")
    return obj


def _get_contractor_capacity_for_update(
    db: Session, contractor_id: int, current_user: User | None = None
) -> ContractorCapacity:
    stmt = select(ContractorCapacity).where(ContractorCapacity.id == contractor_id).with_for_update()
    if current_user is not None:
        stmt = apply_contractor_capacity_read_scope(stmt, current_user)
    obj = db.scalar(stmt)
    if obj is None:
        raise BusinessException(FORBIDDEN if current_user is not None else BAD_REQUEST, "无权访问该承包商运力" if current_user is not None else "承包商运力记录不存在")
    if current_user is not None and not can_manage_contractor_capacity(current_user, obj):
        raise BusinessException(FORBIDDEN, "无权操作该承包商运力")
    return obj


def dispatch_operation(
    db: Session,
    sheet_id: int,
    contractor_capacity_id: int,
    *,
    operator_id: int,
    operator_ip: str | None,
    current_user: User | None = None,
) -> WorkoverOperationSheet:
    """分配上修队伍并发起 A5 措施审核办理，含 Redis 分布式锁防重机制。"""
    # Always lock the work order before its capacity to avoid deadlocks.
    operation_lock = acquire_operation_lock(sheet_id)
    if not operation_lock:
        raise BusinessException(CONFLICT, "该工单正在被其他调度员操作，请稍后重试")
    capacity_lock = acquire_dispatch_lock(contractor_capacity_id)
    if not capacity_lock:
        release_operation_lock(sheet_id, operation_lock)
        raise BusinessException(CONFLICT, "该队伍正在被其他调度员操作，请稍后重试")

    try:
        # Re-read under row locks after acquiring distributed locks.
        sheet = _get_operation_sheet_for_update(db, sheet_id, current_user)
        if sheet.status != OperationStatus.WAITING_DISPATCH:
            raise BusinessException(CONFLICT, f"工单 {sheet.operation_no} 当前状态不允许派工")
        if sheet.contractor_capacity_id is not None:
            raise BusinessException(CONFLICT, f"工单 {sheet.operation_no} 已分配队伍，等待 A5 审核下发")

        # 3. 检查承包商状态
        contractor = _get_contractor_capacity_for_update(db, contractor_capacity_id, current_user)
        if contractor.status != ContractorCapacityStatus.AVAILABLE:
            raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 当前状态不可用")
        if contractor.sync_status != ContractorCapacitySyncStatus.SYNCED:
            raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 的运力尚未确认，不能派工")
        today = datetime.now(BUSINESS_TZ).date()
        if contractor.report_date != today:
            raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 不是当日报备运力，不能派工")
        if contractor.qualification_expire_at is None:
            raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 未维护施工资质有效期")
        if contractor.qualification_expire_at < today:
            raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 的施工资质已过期")
        measures = (sheet.project.measures_jsonb or {}).get("measures", []) if sheet.project else []
        required_capabilities = {
            str(item.get("measure_type")).strip()
            for item in measures
            if isinstance(item, dict) and item.get("measure_type")
        }
        missing_capabilities = sorted(
            capability
            for capability in required_capabilities
            if contractor.capability_tags.get(CAPABILITY_ALIASES.get(capability, capability)) not in {True, "true", 1}
        )
        if missing_capabilities:
            raise BusinessException(
                CONFLICT,
                f"承包商 {contractor.contractor_name} 缺少施工能力：{', '.join(missing_capabilities)}",
            )
        if contractor.available_count <= 0:
            raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 今日可用队伍数不足")

        # 4. 完成本地队伍分配，等待 A5 措施审核及下发
        before = _sheet_snapshot(sheet)
        sheet.contractor_capacity_id = contractor_capacity_id
        sheet.status = OperationStatus.PENDING_A5
        if sheet.project is not None and sheet.project.status == ProjectPoolStatus.APPROVED:
            sheet.project.status = ProjectPoolStatus.DISPATCHED
        sheet.a5_status = "待措施审核"
        sheet.a5_remark = "已分配上修队伍，等待进入A5完成措施审核及下发"
        sheet.last_a5_sync_at = None
        sheet.last_a5_report_date = None
        sheet.a5_sync_result = "PENDING"
        sheet.a5_sync_error = None
        dispatched_at = datetime.now(timezone.utc)
        sheet.dispatched_at = dispatched_at
        detail = dict(sheet.progress_detail or {})
        detail["dispatch"] = {
            "source": "local_dispatch",
            "contractor_capacity_id": contractor_capacity_id,
            "contractor_name": contractor.contractor_name,
            "team_name": contractor.team_name,
            "a5_next_step": "measure_review",
            "updated_at": dispatched_at.isoformat(),
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
        release_dispatch_lock(contractor_capacity_id, capacity_lock)
        release_operation_lock(sheet_id, operation_lock)


def update_sheet_progress(
    db: Session,
    sheet_id: int,
    payload: ProgressPatch,
    *,
    operator_id: int,
    operator_ip: str | None,
    current_user: User | None = None,
) -> WorkoverOperationSheet:
    operation_lock = acquire_operation_lock(sheet_id)
    if not operation_lock:
        raise BusinessException(CONFLICT, "该工单正在被其他调度员操作，请稍后重试")
    capacity_lock: str | bool | None = None
    contractor_id: int | None = None
    try:
        sheet = _get_operation_sheet_for_update(db, sheet_id, current_user)
        if sheet.status == OperationStatus.CANCELED:
            raise BusinessException(CONFLICT, "已取消工单不允许更新施工进度")
        if sheet.status == OperationStatus.FINISHED:
            if payload.progress != 100:
                raise BusinessException(CONFLICT, "已完工工单不允许撤销完工或回退进度")
            return sheet
        if sheet.status in {OperationStatus.WAITING_DISPATCH, OperationStatus.PENDING_A5}:
            message = "待派工工单尚未分配队伍" if sheet.status == OperationStatus.WAITING_DISPATCH else "A5措施尚未审核下发"
            raise BusinessException(CONFLICT, f"{message}，不能更新施工进度")
        if payload.progress < sheet.progress:
            raise BusinessException(CONFLICT, "施工进度不允许回退")
        if sheet.status in {OperationStatus.DISPATCHED, OperationStatus.WORKING} and payload.progress == 0:
            raise BusinessException(CONFLICT, "已派工或施工中工单的进度必须大于 0")
        if payload.progress == 100 and not sheet.a5_status:
            raise BusinessException(CONFLICT, "A5 审核并下发前不允许直接完工")

        contractor_id = sheet.contractor_capacity_id
        finishing_with_contractor = (
            payload.progress == 100
            and sheet.status in {OperationStatus.DISPATCHED, OperationStatus.WORKING}
            and contractor_id is not None
        )
        if finishing_with_contractor:
            capacity_lock = acquire_dispatch_lock(contractor_id)
            if not capacity_lock:
                raise BusinessException(CONFLICT, "该队伍正在被其他调度员操作，请稍后重试")
            # Redis may have been waited on; obtain fresh state before releasing capacity.
            db.expire_all()
            sheet = _get_operation_sheet_for_update(db, sheet_id, current_user)
            if sheet.status == OperationStatus.FINISHED:
                return sheet

        before = _sheet_snapshot(sheet)
        sheet.progress = payload.progress
        detail = dict(sheet.progress_detail or {})
        if payload.progress_detail:
            # User input must not overwrite system-owned dispatch/material/A5 snapshots.
            detail["runtime_management"] = dict(payload.progress_detail)
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
                _release_contractor_capacity(sheet.contractor_capacity)

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
    except Exception:
        db.rollback()
        raise
    finally:
        if capacity_lock and contractor_id is not None:
            release_dispatch_lock(contractor_id, capacity_lock)
        release_operation_lock(sheet_id, operation_lock)


def select_priority_sheets(db: Session, *, current_user: User | None = None) -> list[WorkoverOperationSheet]:
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
    if current_user is not None:
        stmt = apply_workover_operation_scope(stmt, current_user)
    return list(db.scalars(stmt).all())


def get_operation_analytics(db: Session, *, current_user: User | None = None) -> dict[str, Any]:
    """修井运行基础统计。

    统计内容：运行状态分布、派工情况、队伍工作量、措施类型分布、近30天趋势。
    """
    stmt = (
        select(WorkoverOperationSheet)
        .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
        .options(
            selectinload(WorkoverOperationSheet.project),
            selectinload(WorkoverOperationSheet.contractor_capacity),
        )
    )
    if current_user is not None:
        stmt = apply_workover_operation_scope(stmt, current_user)
    sheets = list(db.scalars(stmt).all())

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
    pending_a5 = status_counts.get("PENDING_A5", 0)
    working = status_counts.get("WORKING", 0)
    finished = status_counts.get("FINISHED", 0)
    waiting = status_counts.get("WAITING_DISPATCH", 0)
    canceled = status_counts.get("CANCELED", 0)

    dispatch_rate = round((pending_a5 + dispatched + working + finished) / total * 100, 1) if total > 0 else 0
    completion_rate = round(finished / total * 100, 1) if total > 0 else 0

    return {
        "total_sheets": total,
        "status_distribution": {
            "waiting_dispatch": waiting,
            "pending_a5": pending_a5,
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
