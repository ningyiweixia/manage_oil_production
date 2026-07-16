from datetime import date, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.completion import CompletionAnalyticsQuery, get_completion_analytics
from app.crud.material import MaterialAnalyticsQuery, get_material_analytics
from app.schemas.a5_integration import A5AnalyticsOut, A5AnalyticsQuery
from app.services.data_quality_service import build_data_quality_summary
from app.schemas.workover_project_pool import WorkoverAnalyticsQuery
from app.services.a5_sync_service import build_a5_analytics
from app.services.workover_analytics_service import build_workover_analytics
from app.services.workover_operation_service import OperationAnalyticsQuery, build_workover_operation_dashboard
from app.models.approval import ApprovalAction, ApprovalLog
from app.models.integration import IntegrationEvent, IntegrationEventStatus
from app.models.rbac import User
from app.models.workover import WorkoverOperationSheet, WorkoverProjectPool
from app.services.data_scope_service import DataScope, reporting_unit_scope_predicate


class StatisticsAnalysisQuery(BaseModel):
    """Query model for the plan-defined data statistics analysis module."""

    start_date: date | None = Field(default=None, description="Start date for report statistics")
    end_date: date | None = Field(default=None, description="End date for report statistics")
    well_no: str | None = Field(default=None, description="Well number")
    report_unit: str | None = Field(default=None, description="Reporting unit")
    measure_type: str | None = Field(default=None, description="Measure type")
    team_name: str | None = Field(default=None, description="Operation team")
    process_type: str | None = Field(default=None, description="A5 process type")
    material_status: str | None = Field(default=None, description="Material status")
    block_name: str | None = Field(default=None, description="Block name")
    status: str | None = Field(default=None, description="Project approval status")
    compare_type: Literal["mom", "yoy", "wow", "none"] = Field(default="none", description="Comparison mode: month-over-month / year-over-year / week-over-week")

    @model_validator(mode="after")
    def validate_date_range(self) -> "StatisticsAnalysisQuery":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


TRACE_SOURCES = [
    "workover_project_pool",
    "approval_log",
    "workover_operation_sheet",
    "a5_sync_cache",
    "material_requirement",
    "well_completion_record",
]


def _compute_compare_period(query: StatisticsAnalysisQuery) -> tuple[date | None, date | None]:
    """Compute the previous period date range for comparison."""
    if query.compare_type == "none" or not (query.start_date and query.end_date):
        return None, None
    period_days = (query.end_date - query.start_date).days + 1
    if query.compare_type == "wow":
        prev_end = query.start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days - 1)
    elif query.compare_type == "mom":
        # Approximate: previous period of same length
        prev_end = query.start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days - 1)
    elif query.compare_type == "yoy":
        # Same period, one year back
        prev_start = query.start_date.replace(year=query.start_date.year - 1)
        prev_end = query.end_date.replace(year=query.end_date.year - 1)
    else:
        return None, None
    return prev_start, prev_end


def _compute_comparison(
    current_kpis: dict[str, Any],
    prev_kpis: dict[str, Any],
) -> dict[str, Any]:
    """Compute period-over-period comparison deltas."""
    result: dict[str, Any] = {"mode": "none", "deltas": {}}
    compare_keys = [
        "total_projects", "pending_approvals", "approval_rate",
        "estimated_cost", "operation_sheets", "a5_anomalies",
        "material_requirements", "completion_records",
        "measure_effective_rate", "total_daily_oil_gain",
    ]
    for key in compare_keys:
        cur = float(current_kpis.get(key) or 0)
        prev = float(prev_kpis.get(key) or 0)
        if prev == 0 and cur == 0:
            delta_pct = 0.0
        elif prev == 0:
            delta_pct = 100.0 if cur > 0 else 0.0
        else:
            delta_pct = round((cur - prev) / prev * 100, 2)
        result["deltas"][key] = {
            "current": cur,
            "previous": prev,
            "change": round(cur - prev, 2),
            "change_pct": delta_pct,
        }
    return result


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if isinstance(value, tuple):
        return [_dump(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}
    return value


def _name_value_items(items: Any) -> list[dict[str, Any]]:
    dumped = _dump(items or [])
    if not isinstance(dumped, list):
        return []
    result: list[dict[str, Any]] = []
    for item in dumped:
        if isinstance(item, dict):
            result.append(item)
        else:
            result.append({"name": getattr(item, "name", ""), "value": getattr(item, "value", 0)})
    return result


def _status_name_value(status_counts: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    dumped = _dump(status_counts or [])
    if not isinstance(dumped, list):
        return result
    for item in dumped:
        if isinstance(item, dict):
            result.append(
                {
                    "name": item.get("label") or item.get("status"),
                    "value": item.get("count", 0),
                    "status": item.get("status"),
                }
            )
    return result


def _material_status_distribution(material_usage: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {
        "pending": "待处理",
        "approved": "已审核",
        "planned": "已计划",
        "delivered": "已出库",
        "arrived": "已到场",
        "used": "已使用",
        "canceled": "已取消",
    }
    return [{"name": label, "value": int(material_usage.get(key) or 0)} for key, label in labels.items()]


def _completion_distribution(completion: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"name": item.get("measure_type", "未分类"), "value": int(item.get("count") or 0)}
        for item in completion.get("by_measure_type", [])
    ]


def _build_workover_query(query: StatisticsAnalysisQuery) -> WorkoverAnalyticsQuery:
    return WorkoverAnalyticsQuery(
        start_date=query.start_date,
        end_date=query.end_date,
        status=query.status,
        measure_type=query.measure_type,
        block_name=query.block_name,
        report_unit=query.report_unit,
    )


def _build_a5_query(query: StatisticsAnalysisQuery) -> A5AnalyticsQuery:
    return A5AnalyticsQuery(
        start_date=query.start_date,
        end_date=query.end_date,
        category=query.process_type,
    )


def build_integration_status(db: Session, *, scope: DataScope | None = None) -> dict[str, Any]:
    def count(source: str, status: IntegrationEventStatus) -> int:
        statement = (
            select(func.count())
            .select_from(IntegrationEvent)
            .where(IntegrationEvent.source == source, IntegrationEvent.status == status)
        )
        if scope is not None and not scope.is_global:
            if source != "a5" or not scope.reporting_units:
                return 0
            statement = (
                statement.join(WorkoverOperationSheet, IntegrationEvent.operation_no == WorkoverOperationSheet.operation_no)
                .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
                .where(reporting_unit_scope_predicate(scope))
            )
        value = db.scalar(statement)
        return int(value) if isinstance(value, (int, float)) else 0

    return {
        "a5_adapter_mode": settings.a5_adapter_mode,
        "material_adapter_mode": settings.material_adapter_mode,
        "a5_processed": count("a5", IntegrationEventStatus.PROCESSED),
        "a5_pending_review": count("a5", IntegrationEventStatus.PENDING_REVIEW),
        "a5_failed": count("a5", IntegrationEventStatus.FAILED),
        "material_processed": count("material", IntegrationEventStatus.PROCESSED),
    }


def build_approval_efficiency(
    db: Session,
    query: StatisticsAnalysisQuery,
    *,
    scope: DataScope | None = None,
) -> dict[str, Any]:
    """审批效率分析：各阶段平均耗时、瓶颈节点、驳回率、审批人工作量。"""
    NODE_LABELS = {
        "GEOLOGY_VERIFY": "地质核实",
        "PROCESS_VERIFY": "工艺核实",
        "PENDING_GEOLOGY_VERIFY": "地质核实",
        "PENDING_PROCESS_VERIFY": "工艺核实",
    }

    # Query project pool approval logs
    stmt = select(ApprovalLog).where(
        ApprovalLog.business_type == "workover_project_pool",
        ApprovalLog.action.in_([ApprovalAction.APPROVE, ApprovalAction.REJECT, ApprovalAction.SUBMIT]),
    )
    if query.start_date:
        stmt = stmt.where(ApprovalLog.created_at >= query.start_date)
    if query.end_date:
        stmt = stmt.where(ApprovalLog.created_at < query.end_date + timedelta(days=1))
    stmt = stmt.order_by(ApprovalLog.business_id, ApprovalLog.created_at.asc())

    if scope is not None and not scope.is_global:
        stmt = stmt.join(WorkoverProjectPool, ApprovalLog.business_id == WorkoverProjectPool.id)
        stmt = stmt.where(reporting_unit_scope_predicate(scope))

    logs = list(db.scalars(stmt).all())

    # Group by business_id to compute stage durations
    business_logs: dict[int, list[ApprovalLog]] = {}
    for log in logs:
        business_logs.setdefault(log.business_id, []).append(log)

    stage_durations: dict[str, list[float]] = {}  # node_code -> list of hours
    approver_counts: dict[int, dict[str, Any]] = {}  # operator_id -> {name, approve_count, reject_count}
    reject_reasons: dict[str, int] = {}  # reason -> count
    total_approvals = 0
    total_rejections = 0

    for bid, bid_logs in business_logs.items():
        for i in range(len(bid_logs) - 1):
            curr = bid_logs[i]
            next_log = bid_logs[i + 1]
            hours = (next_log.created_at - curr.created_at).total_seconds() / 3600
            if hours < 0 or hours > 720:  # skip unreasonable durations (>30 days)
                continue
            node = NODE_LABELS.get(curr.node_code, curr.node_code)
            stage_durations.setdefault(node, []).append(hours)

        for log in bid_logs:
            if log.action == ApprovalAction.APPROVE:
                total_approvals += 1
            elif log.action == ApprovalAction.REJECT:
                total_rejections += 1
                reason = (log.comment or "未填写原因")[:30]
                reject_reasons[reason] = reject_reasons.get(reason, 0) + 1

            if log.operator_id:
                entry = approver_counts.setdefault(log.operator_id, {
                    "operator_id": log.operator_id,
                    "operator_name": log.operator.full_name if log.operator else f"用户{log.operator_id}",
                    "approve_count": 0,
                    "reject_count": 0,
                    "total_actions": 0,
                })
                if log.action == ApprovalAction.APPROVE:
                    entry["approve_count"] += 1
                elif log.action == ApprovalAction.REJECT:
                    entry["reject_count"] += 1
                entry["total_actions"] += 1

    # Compute stage averages
    stage_summary = []
    bottleneck_node = None
    bottleneck_hours = 0.0
    bottleneck_samples = 0
    for node, durations in sorted(stage_durations.items()):
        avg_h = round(sum(durations) / len(durations), 1) if durations else 0
        stage_summary.append({
            "node": node,
            "avg_hours": avg_h,
            "sample_count": len(durations),
            "max_hours": round(max(durations), 1) if durations else 0,
        })
        if avg_h > bottleneck_hours or (avg_h == bottleneck_hours and len(durations) > bottleneck_samples):
            bottleneck_hours = avg_h
            bottleneck_node = node
            bottleneck_samples = len(durations)

    # Sort approvers by workload
    top_approvers = sorted(approver_counts.values(), key=lambda x: -x["total_actions"])[:10]

    # Rejection reasons sorted by frequency
    top_reject_reasons = [
        {"reason": k, "count": v}
        for k, v in sorted(reject_reasons.items(), key=lambda x: -x[1])[:10]
    ]

    total_actions = total_approvals + total_rejections
    return {
        "total_actions": total_actions,
        "total_approvals": total_approvals,
        "total_rejections": total_rejections,
        "rejection_rate": round(total_rejections / total_actions * 100, 2) if total_actions else 0,
        "stage_summary": stage_summary,
        "bottleneck": {
            "node": bottleneck_node,
            "avg_hours": bottleneck_hours,
        },
        "top_reject_reasons": top_reject_reasons,
        "top_approvers": top_approvers,
    }


def build_contractor_performance(
    db: Session,
    query: StatisticsAnalysisQuery,
    *,
    scope: DataScope | None = None,
) -> list[dict[str, Any]]:
    """承包商综合评价：按作业队伍统计完工表现、增产效果与异常情况。"""
    from app.models.completion import WellCompletionRecord

    stmt = select(WellCompletionRecord).join(WorkoverOperationSheet).join(WorkoverProjectPool)
    if scope is not None and not scope.is_global:
        stmt = stmt.where(reporting_unit_scope_predicate(scope))
    if query.start_date:
        stmt = stmt.where(WellCompletionRecord.completion_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(WellCompletionRecord.completion_date <= query.end_date)
    if query.team_name:
        stmt = stmt.where(WellCompletionRecord.team_name.ilike(f"%{query.team_name}%"))

    records = list(db.scalars(stmt).all())

    # Group by team
    teams: dict[str, dict[str, Any]] = {}
    for rec in records:
        team = rec.team_name or "未指定队伍"
        if team not in teams:
            teams[team] = {
                "team_name": team,
                "completed_count": 0,
                "effective_count": 0,
                "total_oil_gain": 0.0,
                "a5_anomaly_count": 0,
                "completion_dates": [],
            }
        t = teams[team]
        t["completed_count"] += 1
        pre = rec.pre_repair_data or {}
        post = rec.post_repair_data or {}
        pre_oil = float(pre.get("daily_oil", 0) or 0)
        post_oil = float(post.get("daily_oil", 0) or 0)
        if post_oil > pre_oil:
            t["effective_count"] += 1
            t["total_oil_gain"] += post_oil - pre_oil

        if rec.completion_date:
            t["completion_dates"].append(rec.completion_date)

        # Check A5 anomaly via operation sheet
        try:
            sheet = rec.operation_sheet
            if sheet and str(sheet.a5_status or "").upper() in {"ANOMALY", "ERROR", "EXCEPTION", "FAILED"}:
                t["a5_anomaly_count"] += 1
        except Exception:
            pass

    # Compute scores
    result = []
    for team, data in teams.items():
        cnt = data["completed_count"]
        data["effective_rate"] = round(data["effective_count"] / cnt * 100, 2) if cnt else 0
        data["avg_oil_gain"] = round(data["total_oil_gain"] / data["effective_count"], 2) if data["effective_count"] else 0
        # Composite score: 40% effective rate + 30% oil gain (normalized) + 30% (1 - anomaly rate)
        gain_score = min(data["avg_oil_gain"] / 5.0 * 100, 100) if data["avg_oil_gain"] > 0 else 50
        anomaly_rate = data["a5_anomaly_count"] / cnt if cnt else 0
        anomaly_score = max(0, (1 - anomaly_rate) * 100)
        data["score"] = round(
            data["effective_rate"] * 0.4 + gain_score * 0.3 + anomaly_score * 0.3, 1
        )
        # Clean up non-serializable
        del data["completion_dates"]
        result.append(data)

    return sorted(result, key=lambda x: -x["score"])


def build_statistics_analysis(
    db: Session,
    query: StatisticsAnalysisQuery,
    *,
    scope: DataScope | None = None,
) -> dict[str, Any]:
    """Aggregate production analysis, review, and report data into one payload."""

    if scope is not None and not scope.is_global:
        query = query.model_copy(update={"report_unit": scope.department or "__no_scope__"})

    workover = build_workover_analytics(db, _build_workover_query(query), scope=scope)
    operation_query = OperationAnalyticsQuery(
        start_date=query.start_date, end_date=query.end_date, well_no=query.well_no,
        report_unit=query.report_unit, team_name=query.team_name, block_name=query.block_name,
        status=query.status, measure_type=query.measure_type, material_status=query.material_status,
    )
    operation_args = (
        {"scope": scope}
        if scope is not None
        else {}
    )
    operation_efficiency = _dump(build_workover_operation_dashboard(
        db, operation_query if any(operation_query.model_dump().values()) else None, **operation_args
    ))
    material_usage = _dump(get_material_analytics(db, MaterialAnalyticsQuery(
        start_date=query.start_date, end_date=query.end_date, well_no=query.well_no,
        status=query.material_status,
    ), scope=scope))
    completion_classification = _dump(get_completion_analytics(db, CompletionAnalyticsQuery(
        start_date=query.start_date, end_date=query.end_date, well_no=query.well_no,
        measure_type=query.measure_type, team_name=query.team_name, report_unit=query.report_unit,
    ), scope=scope))
    # Cached A5 analytics records do not yet carry report-unit ownership.  Do
    # not expose that shared cache to scoped users until the upstream contract
    # provides a reliable ownership field.
    a5 = A5AnalyticsOut() if scope is not None and not scope.is_global else build_a5_analytics(_build_a5_query(query))
    data_quality = _dump(build_data_quality_summary(db, query, scope=scope))
    integration_status = build_integration_status(db, scope=scope)
    approval_efficiency = build_approval_efficiency(db, query, scope=scope)
    contractor_performance = build_contractor_performance(db, query, scope=scope)

    overview_kpis = {
        "total_projects": workover.kpis.total_projects,
        "pending_approvals": workover.kpis.pending_approvals,
        "approval_rate": workover.kpis.approval_rate,
        "estimated_cost": workover.kpis.estimated_cost,
        "operation_sheets": operation_efficiency.get("total_sheets", 0),
        "a5_anomalies": a5.anomaly_total,
        "material_requirements": material_usage.get("total", 0),
        "completion_records": completion_classification.get("total", 0),
        "data_quality_issues": data_quality.get("total_issues", 0),
        # 修井效果评估
        "measure_effective_rate": completion_classification.get("production_gain", {}).get("effective_rate", 0),
        "total_daily_oil_gain": completion_classification.get("production_gain", {}).get("total_daily_oil_gain", 0),
        "monthly_gain_tons": completion_classification.get("production_gain", {}).get("monthly_gain_tons", 0),
        "avg_cost_per_ton": completion_classification.get("production_gain", {}).get("avg_cost_per_ton", 0),
    }

    # Period-over-period comparison
    comparison: dict[str, Any] = {"mode": query.compare_type, "deltas": {}}
    if query.compare_type != "none":
        prev_start, prev_end = _compute_compare_period(query)
        if prev_start and prev_end:
            prev_query = _build_workover_query(query.model_copy(update={"start_date": prev_start, "end_date": prev_end}))
            prev_workover = build_workover_analytics(db, prev_query, scope=scope)
            prev_kpis = {
                "total_projects": prev_workover.kpis.total_projects,
                "pending_approvals": prev_workover.kpis.pending_approvals,
                "approval_rate": prev_workover.kpis.approval_rate,
                "estimated_cost": prev_workover.kpis.estimated_cost,
                "operation_sheets": 0, "a5_anomalies": 0,
                "material_requirements": 0, "completion_records": 0,
                "measure_effective_rate": 0, "total_daily_oil_gain": 0,
            }
            comparison = _compute_comparison(overview_kpis, prev_kpis)
            comparison["mode"] = query.compare_type
            comparison["prev_period"] = {"start_date": prev_start.isoformat(), "end_date": prev_end.isoformat()}

    a5_statistics = {
        "anomaly_total": a5.anomaly_total,
        "special_process_total": a5.special_process_total,
        "anomaly_distribution": _name_value_items(a5.anomaly_distribution),
        "process_distribution": _name_value_items(a5.process_distribution),
        "trend": _dump(getattr(a5, "trend", None)),
    }

    chart_series = {
        "approval_status": _status_name_value(workover.status_counts),
        "measure_distribution": _name_value_items(workover.measure_distribution),
        "block_status_heatmap": _dump(workover.heatmap),
        "submission_trend": _dump(workover.trend),
        "a5_anomaly_trend": a5_statistics["trend"],
        "material_status_distribution": _material_status_distribution(material_usage),
        "team_workload_rank": operation_efficiency.get("team_workload", []),
        "completion_measure_distribution": _completion_distribution(completion_classification),
        # 修井效果评估图表数据
        "production_gain_by_measure": completion_classification.get("by_measure_effect", []),
        "production_gain_summary": completion_classification.get("production_gain", {}),
        # 审批效率
        "approval_stage_summary": approval_efficiency.get("stage_summary", []),
        "approval_bottleneck": approval_efficiency.get("bottleneck", {}),
        # 承包商绩效
        "contractor_performance_scores": contractor_performance,
    }

    return {
        "query": query.model_dump(mode="json"),
        "overview_kpis": overview_kpis,
        "operation_efficiency": operation_efficiency,
        "a5_statistics": a5_statistics,
        "material_usage": material_usage,
        "completion_classification": completion_classification,
        "data_quality_summary": data_quality,
        "integration_status": integration_status,
        "approval_efficiency": approval_efficiency,
        "contractor_performance": contractor_performance,
        "trace_sources": TRACE_SOURCES,
        "comparison": comparison,
        "chart_series": chart_series,
        "report_outputs": ["statistics_dashboard", "excel_report", "word_report", "analysis_summary", "data_quality_summary", "approval_efficiency"],
    }
