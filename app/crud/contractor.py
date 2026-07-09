import uuid
from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessException
from app.core.redis import cache_client
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.models.approval import ApprovalAction
from app.models.workover import (
    ContractorCapacity,
    ContractorCapacityStatus,
    OperationStatus,
    ProjectPoolStatus,
    WorkoverOperationSheet,
    WorkoverProjectPool,
)
from app.schemas.contractor import (
    ContractorCapacityCreate,
    ContractorCapacityQuery,
    ContractorCapacityUpdate,
    DispatchPayload,
    ProgressPatch,
    WorkoverOperationSheetCreate,
    WorkoverOperationSheetQuery,
    WorkoverOperationSheetUpdate,
)
from app.services.audit_service import write_approval_log
from app.services.dictionary_service import ensure_dictionary_values

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
    if query.report_date:
        stmt = stmt.where(ContractorCapacity.report_date == query.report_date)
    if query.status:
        stmt = stmt.where(ContractorCapacity.status == query.status)
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
    base_stmt = _apply_contractor_filters(select(ContractorCapacity), query)
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
