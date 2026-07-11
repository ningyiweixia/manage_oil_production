from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.completion import WellCompletionRecord
from app.models.material import MaterialRequirement, MaterialRequirementStatus
from app.models.workover import ContractorCapacity, ContractorCapacitySyncStatus, OperationStatus, ProjectPoolStatus, WorkoverOperationSheet, WorkoverProjectPool
from app.schemas.analytics import DataQualityIssueOut, DataQualitySummaryOut

_SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1}


def _issue(
    *,
    rule_code: str,
    title: str,
    severity: str,
    message: str,
    entity_type: str,
    entity_id: int | None = None,
    well_no: str | None = None,
    team_name: str | None = None,
    suggestion: str | None = None,
) -> DataQualityIssueOut:
    return DataQualityIssueOut(
        rule_code=rule_code,
        title=title,
        severity=severity,  # type: ignore[arg-type]
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        well_no=well_no,
        team_name=team_name,
        suggestion=suggestion,
    )


def _apply_sheet_filters(stmt, query):
    stmt = stmt.join(WorkoverProjectPool).outerjoin(ContractorCapacity)
    if query.well_no:
        stmt = stmt.where(WorkoverProjectPool.well_no.ilike(f"%{query.well_no}%"))
    if query.report_unit:
        stmt = stmt.where(WorkoverProjectPool.report_unit.ilike(f"%{query.report_unit}%"))
    if query.team_name:
        stmt = stmt.where(ContractorCapacity.team_name.ilike(f"%{query.team_name}%"))
    if query.block_name:
        stmt = stmt.where(WorkoverProjectPool.block_name.ilike(f"%{query.block_name}%"))
    if query.status:
        stmt = stmt.where(WorkoverProjectPool.status == query.status)
    if query.measure_type:
        stmt = stmt.where(cast(WorkoverProjectPool.measures_jsonb, String).ilike(f"%{query.measure_type}%"))
    if query.start_date:
        stmt = stmt.where(WorkoverOperationSheet.created_at >= datetime.combine(query.start_date, time.min))
    if query.end_date:
        stmt = stmt.where(WorkoverOperationSheet.created_at < datetime.combine(query.end_date + timedelta(days=1), time.min))
    return stmt


def _scoped_sheets(db: Session, query) -> list[WorkoverOperationSheet]:
    stmt = (
        select(WorkoverOperationSheet)
        .options(selectinload(WorkoverOperationSheet.project), selectinload(WorkoverOperationSheet.contractor_capacity))
    )
    stmt = _apply_sheet_filters(stmt, query)
    try:
        return list(db.scalars(stmt).all())
    except TypeError:
        return []


def _scoped_materials(db: Session, query) -> list[MaterialRequirement]:
    stmt = select(MaterialRequirement)
    if query.well_no:
        stmt = stmt.where(MaterialRequirement.well_no.ilike(f"%{query.well_no}%"))
    if query.material_status:
        stmt = stmt.where(MaterialRequirement.status == query.material_status)
    if query.start_date:
        stmt = stmt.where(MaterialRequirement.created_at >= datetime.combine(query.start_date, time.min))
    if query.end_date:
        stmt = stmt.where(MaterialRequirement.created_at < datetime.combine(query.end_date + timedelta(days=1), time.min))
    try:
        return list(db.scalars(stmt).all())
    except TypeError:
        return []


def _scoped_contractors(db: Session, query) -> list[ContractorCapacity]:
    stmt = select(ContractorCapacity)
    if query.team_name:
        stmt = stmt.where(ContractorCapacity.team_name.ilike(f"%{query.team_name}%"))
    try:
        return list(db.scalars(stmt).all())
    except TypeError:
        return []


def _missing_a5_link_issues(sheets: Iterable[WorkoverOperationSheet]) -> list[DataQualityIssueOut]:
    issues: list[DataQualityIssueOut] = []
    for sheet in sheets:
        if not sheet.a5_status or sheet.last_a5_sync_at is None:
            issues.append(
                _issue(
                    rule_code="A5_LINK_MISSING",
                    title="A5 关联缺失",
                    severity="medium",
                    message=f"作业单 {sheet.operation_no} 缺少 A5 同步状态或同步时间。",
                    entity_type="workover_operation_sheet",
                    entity_id=sheet.id,
                    well_no=sheet.project_well_no,
                    team_name=sheet.contractor_capacity.team_name if sheet.contractor_capacity else None,
                    suggestion="补齐 A5 同步信息或重新触发同步。",
                )
            )
    return issues


def _time_order_issues(sheets: Iterable[WorkoverOperationSheet]) -> list[DataQualityIssueOut]:
    issues: list[DataQualityIssueOut] = []
    for sheet in sheets:
        if sheet.planned_start_at and sheet.planned_end_at and sheet.planned_start_at > sheet.planned_end_at:
            issues.append(
                _issue(
                    rule_code="PLAN_TIME_ORDER",
                    title="计划时间顺序错误",
                    severity="high",
                    message=f"作业单 {sheet.operation_no} 的计划开始时间晚于计划结束时间。",
                    entity_type="workover_operation_sheet",
                    entity_id=sheet.id,
                    well_no=sheet.project_well_no,
                    team_name=sheet.contractor_capacity.team_name if sheet.contractor_capacity else None,
                    suggestion="修正计划开始/结束时间。",
                )
            )
        if sheet.actual_start_at and sheet.actual_end_at and sheet.actual_start_at > sheet.actual_end_at:
            issues.append(
                _issue(
                    rule_code="ACTUAL_TIME_ORDER",
                    title="实际时间顺序错误",
                    severity="high",
                    message=f"作业单 {sheet.operation_no} 的实际开始时间晚于实际结束时间。",
                    entity_type="workover_operation_sheet",
                    entity_id=sheet.id,
                    well_no=sheet.project_well_no,
                    team_name=sheet.contractor_capacity.team_name if sheet.contractor_capacity else None,
                    suggestion="核对现场完工时间并回填。",
                )
            )
        if sheet.project and sheet.project.approved_at and sheet.planned_start_at and sheet.project.approved_at > sheet.planned_start_at:
            issues.append(
                _issue(
                    rule_code="APPROVAL_AFTER_START",
                    title="审批晚于开工",
                    severity="medium",
                    message=f"作业单 {sheet.operation_no} 的审批通过时间晚于计划开工时间。",
                    entity_type="workover_operation_sheet",
                    entity_id=sheet.id,
                    well_no=sheet.project_well_no,
                    team_name=sheet.contractor_capacity.team_name if sheet.contractor_capacity else None,
                    suggestion="复核作业单与审批单的时间关系。",
                )
            )
    return issues


def _missing_completion_issues(db: Session, sheets: list[WorkoverOperationSheet]) -> list[DataQualityIssueOut]:
    if not sheets:
        return []
    completed_sheet_ids = set(
        db.scalars(
            select(WellCompletionRecord.operation_sheet_id).where(WellCompletionRecord.operation_sheet_id.in_([sheet.id for sheet in sheets]))
        ).all()
    )
    issues: list[DataQualityIssueOut] = []
    for sheet in sheets:
        if sheet.status == OperationStatus.FINISHED and sheet.id not in completed_sheet_ids:
            issues.append(
                _issue(
                    rule_code="MISSING_COMPLETION",
                    title="完井台账缺失",
                    severity="high",
                    message=f"作业单 {sheet.operation_no} 已完工但未找到对应完井记录。",
                    entity_type="workover_operation_sheet",
                    entity_id=sheet.id,
                    well_no=sheet.project_well_no,
                    team_name=sheet.contractor_capacity.team_name if sheet.contractor_capacity else None,
                    suggestion="补录完井记录或核对作业单状态。",
                )
            )
    return issues


def _material_usage_issues(materials: Iterable[MaterialRequirement]) -> list[DataQualityIssueOut]:
    issues: list[DataQualityIssueOut] = []
    for item in materials:
        if item.delivered_quantity > item.planned_quantity > 0:
            issues.append(
                _issue(
                    rule_code="MATERIAL_PLANNED_EXCEEDED",
                    title="计划量异常",
                    severity="medium",
                    message=f"物料 {item.material_name} 的出库量超过计划量。",
                    entity_type="material_requirement",
                    entity_id=item.id,
                    well_no=item.well_no,
                    suggestion="核对物料计划量和出库量。",
                )
            )
        if item.used_quantity > item.arrived_quantity > 0:
            issues.append(
                _issue(
                    rule_code="MATERIAL_USAGE_EXCEEDED",
                    title="使用量超额",
                    severity="high",
                    message=f"物料 {item.material_name} 的使用量超过到货量。",
                    entity_type="material_requirement",
                    entity_id=item.id,
                    well_no=item.well_no,
                    suggestion="核对到货和领用数据。",
                )
            )
        if item.status == MaterialRequirementStatus.USED and item.used_quantity <= 0:
            issues.append(
                _issue(
                    rule_code="MATERIAL_USAGE_MISSING",
                    title="使用明细缺失",
                    severity="low",
                    message=f"物料 {item.material_name} 已标记为使用完成，但未记录使用数量。",
                    entity_type="material_requirement",
                    entity_id=item.id,
                    well_no=item.well_no,
                    suggestion="补齐使用数量或修正状态。",
                )
            )
    return issues


def _qualification_issues(contractors: Iterable[ContractorCapacity], *, warning_days: int) -> list[DataQualityIssueOut]:
    issues: list[DataQualityIssueOut] = []
    today = date.today()
    warning_date = today + timedelta(days=warning_days)
    for item in contractors:
        if item.qualification_expire_at and item.qualification_expire_at <= warning_date:
            severity = "high" if item.qualification_expire_at < today else "medium"
            issues.append(
                _issue(
                    rule_code="QUALIFICATION_EXPIRING",
                    title="资质临期",
                    severity=severity,
                    message=f"承包商 {item.team_name} 的资质将在 {item.qualification_expire_at} 到期。",
                    entity_type="contractor_capacity",
                    entity_id=item.id,
                    team_name=item.team_name,
                    suggestion="及时复核资质并更新有效期。",
                )
            )
    return issues


def _sync_failure_issues(contractors: Iterable[ContractorCapacity], sheets: Iterable[WorkoverOperationSheet]) -> list[DataQualityIssueOut]:
    issues: list[DataQualityIssueOut] = []
    for item in contractors:
        if item.sync_status in {ContractorCapacitySyncStatus.CONFLICT, ContractorCapacitySyncStatus.INVALID} or item.sync_error_message:
            issues.append(
                _issue(
                    rule_code="CONTRACTOR_SYNC_FAILURE",
                    title="承包商同步失败",
                    severity="high",
                    message=item.sync_error_message or f"承包商 {item.team_name} 的同步状态为 {item.sync_status.value}.",
                    entity_type="contractor_capacity",
                    entity_id=item.id,
                    team_name=item.team_name,
                    suggestion="重新同步或人工确认该承包商班组数据。",
                )
            )
    for sheet in sheets:
        code = (sheet.a5_status or "").upper()
        if code in {"FAILED", "ERROR", "EXCEPTION"}:
            issues.append(
                _issue(
                    rule_code="A5_SYNC_FAILURE",
                    title="A5 同步失败",
                    severity="high",
                    message=f"作业单 {sheet.operation_no} 的 A5 同步结果为 {code}.",
                    entity_type="workover_operation_sheet",
                    entity_id=sheet.id,
                    well_no=sheet.project_well_no,
                    team_name=sheet.contractor_capacity.team_name if sheet.contractor_capacity else None,
                    suggestion="重新触发 A5 同步并检查异常原因。",
                )
            )
    return issues


def build_data_quality_summary(
    db: Session,
    query=None,
    *,
    qualification_warning_days: int = 30,
) -> DataQualitySummaryOut:
    from app.services.statistics_analysis_service import StatisticsAnalysisQuery as _StatisticsAnalysisQuery

    query = query or _StatisticsAnalysisQuery()
    sheets = _scoped_sheets(db, query)
    materials = _scoped_materials(db, query)
    contractors = _scoped_contractors(db, query)

    issues = [
        *_missing_a5_link_issues(sheets),
        *_time_order_issues(sheets),
        *_missing_completion_issues(db, sheets),
        *_material_usage_issues(materials),
        *_qualification_issues(contractors, warning_days=qualification_warning_days),
        *_sync_failure_issues(contractors, sheets),
    ]
    issues.sort(key=lambda item: (-_SEVERITY_ORDER.get(item.severity, 0), item.rule_code, item.entity_type, item.entity_id or 0))
    severity_counts = Counter(issue.severity for issue in issues)

    return DataQualitySummaryOut(
        total_issues=len(issues),
        severity_counts={key: int(severity_counts.get(key, 0)) for key in ("high", "medium", "low")},
        issues=issues,
        scope=query.model_dump(mode="json"),
    )
