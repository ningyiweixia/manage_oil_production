from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.crud.completion import CompletionAnalyticsQuery, get_completion_analytics
from app.crud.material import MaterialAnalyticsQuery, get_material_analytics
from app.schemas.a5_integration import A5AnalyticsQuery
from app.schemas.workover_project_pool import WorkoverAnalyticsQuery
from app.services.a5_sync_service import build_a5_analytics
from app.services.workover_analytics_service import build_workover_analytics
from app.services.workover_operation_service import OperationAnalyticsQuery, build_workover_operation_dashboard


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
    )


def _build_a5_query(query: StatisticsAnalysisQuery) -> A5AnalyticsQuery:
    return A5AnalyticsQuery(
        start_date=query.start_date,
        end_date=query.end_date,
        category=query.process_type,
    )


def build_statistics_analysis(db: Session, query: StatisticsAnalysisQuery) -> dict[str, Any]:
    """Aggregate production analysis, review, and report data into one payload."""

    workover = build_workover_analytics(db, _build_workover_query(query))
    operation_efficiency = _dump(build_workover_operation_dashboard(db, OperationAnalyticsQuery(
        start_date=query.start_date, end_date=query.end_date, well_no=query.well_no,
        report_unit=query.report_unit, team_name=query.team_name, block_name=query.block_name,
        status=query.status,
    )))
    material_usage = _dump(get_material_analytics(db, MaterialAnalyticsQuery(
        start_date=query.start_date, end_date=query.end_date, well_no=query.well_no,
        status=query.material_status,
    )))
    completion_classification = _dump(get_completion_analytics(db, CompletionAnalyticsQuery(
        start_date=query.start_date, end_date=query.end_date, well_no=query.well_no,
        measure_type=query.measure_type, team_name=query.team_name,
    )))
    a5 = build_a5_analytics(_build_a5_query(query))

    overview_kpis = {
        "total_projects": workover.kpis.total_projects,
        "pending_approvals": workover.kpis.pending_approvals,
        "approval_rate": workover.kpis.approval_rate,
        "estimated_cost": workover.kpis.estimated_cost,
        "operation_sheets": operation_efficiency.get("total_sheets", 0),
        "a5_anomalies": a5.anomaly_total,
        "material_requirements": material_usage.get("total", 0),
        "completion_records": completion_classification.get("total", 0),
    }

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
    }

    return {
        "query": query.model_dump(mode="json"),
        "overview_kpis": overview_kpis,
        "operation_efficiency": operation_efficiency,
        "a5_statistics": a5_statistics,
        "material_usage": material_usage,
        "completion_classification": completion_classification,
        "trace_sources": TRACE_SOURCES,
        "chart_series": chart_series,
        "report_outputs": ["statistics_dashboard", "excel_report", "word_report", "analysis_summary"],
    }
