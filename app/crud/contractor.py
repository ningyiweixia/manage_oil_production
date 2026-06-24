import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.redis import cache_client
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.models.approval import ApprovalAction
from app.models.workover import (
    ContractorCapacity,
    ContractorCapacityStatus,
    OperationStatus,
    WorkoverOperationSheet,
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
    base_stmt = _apply_sheet_filters(select(WorkoverOperationSheet), query)
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


def create_operation_sheet(
    db: Session,
    payload: WorkoverOperationSheetCreate,
    *,
    operator_id: int,
    operator_ip: str | None,
) -> WorkoverOperationSheet:
    data = payload.model_dump(mode="json")
    operation_no = f"OP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
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
    return cache_client.set_json(lock_key, {"locked_at": datetime.now(timezone.utc).isoformat()}, expire_seconds=LOCK_TTL)


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
    """派工核心方法，含 Redis 分布式锁防重机制。"""
    # 1. 获取分布式锁
    if not acquire_dispatch_lock(contractor_capacity_id):
        raise BusinessException(CONFLICT, "该队伍正在被其他调度员操作，请稍后重试")

    try:
        # 2. 获取工单
        sheet = get_operation_sheet(db, sheet_id)
        if sheet.status != OperationStatus.WAITING_DISPATCH:
            raise BusinessException(CONFLICT, f"工单 {sheet.operation_no} 当前状态不允许派工")

        # 3. 检查承包商状态
        contractor = get_contractor_capacity(db, contractor_capacity_id)
        if contractor.status != ContractorCapacityStatus.AVAILABLE:
            raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 当前状态不可用")

        # 4. 执行派工
        before = _sheet_snapshot(sheet)
        sheet.contractor_capacity_id = contractor_capacity_id
        sheet.status = OperationStatus.DISPATCHED
        db.flush()

        # 5. 更新承包商状态为忙碌
        contractor.status = ContractorCapacityStatus.BUSY
        db.flush()

        # 6. 写审计日志
        write_approval_log(
            db,
            business_type=BUSINESS_TYPE_OPERATION,
            business_id=sheet.id,
            node_code="DISPATCH",
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
    sheet.progress_detail = payload.progress_detail

    # 自动推进状态
    if payload.progress == 100 and sheet.status == OperationStatus.DISPATCHED:
        sheet.status = OperationStatus.WORKING
        sheet.actual_start_at = datetime.now(timezone.utc)
    elif payload.progress == 100 and sheet.status in {OperationStatus.DISPATCHED, OperationStatus.WORKING}:
        sheet.status = OperationStatus.FINISHED
        sheet.actual_end_at = datetime.now(timezone.utc)

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
    from app.models.workover import WorkoverProjectPool

    stmt = (
        select(WorkoverOperationSheet)
        .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
        .where(WorkoverOperationSheet.status == OperationStatus.WAITING_DISPATCH)
        .order_by(
            WorkoverProjectPool.approved_at.asc().nullslast(),
            WorkoverProjectPool.production_priority.desc(),
        )
    )
    return list(db.scalars(stmt).all())
