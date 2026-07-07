from datetime import date
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.crud.completion import get_completion_analytics
from app.crud.material import get_material_analytics
from app.schemas.a5_integration import A5AnalyticsQuery
from app.schemas.workover_project_pool import WorkoverAnalyticsQuery
from app.services.a5_sync_service import build_a5_analytics
from app.services.workover_analytics_service import build_workover_analytics
from app.services.workover_operation_service import build_workover_operation_dashboard


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
    result: list[dict[str, Any]] = []
    for item in dumped:
        if isinstance(item, dict):
            result.append(item)
        else:
            result.append(
                {
                    "name": getattr(item, "name", ""),
                    "value": getattr(item, "value", 0),
                }
            )
    return result


def _build_workover_query(query: StatisticsAnalysisQuery) -> WorkoverAnalyticsQuery:
    return WorkoverAnalyticsQuery(
        start_date=query.start_date,
        end_date=query.end_date,
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
    """Aggregate the plan's data analysis sections into one report payload."""

    workover = build_workover_analytics(db, _build_workover_query(query))
    operation = build_workover_operation_dashboard(db)
    material_usage = get_material_analytics(db, well_no=query.well_no)
    completion_classification = get_completion_analytics(db)
    a5 = build_a5_analytics(_build_a5_query(query))

    report_key_data = {
        "total_projects": workover.kpis.total_projects,
        "pending_approvals": workover.kpis.pending_approvals,
        "approval_rate": workover.kpis.approval_rate,
        "estimated_cost": workover.kpis.estimated_cost,
        "measure_distribution": _name_value_items(workover.measure_distribution),
        "status_counts": _dump(workover.status_counts),
        "trend": _dump(workover.trend),
        "fields": ["well_no", "measure_type", "construction_result", "main_parameters", "exception_description"],
    }

    a5_statistics = {
        "anomaly_total": a5.anomaly_total,
        "special_process_total": a5.special_process_total,
        "anomaly_distribution": _name_value_items(a5.anomaly_distribution),
        "process_distribution": _name_value_items(a5.process_distribution),
        "trend": _dump(getattr(a5, "trend", None)),
    }

    return {
        "query": query.model_dump(mode="json"),
        "report_key_data": report_key_data,
        "completion_classification": _dump(completion_classification),
        "a5_statistics": a5_statistics,
        "material_usage": _dump(material_usage),
        "operation_efficiency": _dump(operation),
        "trace_sources": TRACE_SOURCES,
        "report_outputs": ["statistics_chart", "excel_report", "word_report", "analysis_summary"],
    }
