from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workover import ProjectPoolStatus, WorkoverProjectPool
from app.services.data_scope_service import DataScope, reporting_unit_scope_predicate
from app.schemas.workover_project_pool import (
    AnalyticsKpiOut,
    HeatmapOut,
    NameValueOut,
    StatusCountOut,
    TrendOut,
    WorkoverAnalyticsOut,
    WorkoverAnalyticsQuery,
)

STATUS_LABELS: dict[ProjectPoolStatus, str] = {
    ProjectPoolStatus.DRAFT: "草稿",
    ProjectPoolStatus.PENDING_GEOLOGY_VERIFY: "待地质核实",
    ProjectPoolStatus.PENDING_PROCESS_VERIFY: "待工艺核实",
    ProjectPoolStatus.APPROVED: "已入库",
    ProjectPoolStatus.REJECTED: "已驳回",
    ProjectPoolStatus.DISPATCHED: "已派工",
}

STATUS_COUNT_ORDER = [
    ProjectPoolStatus.DRAFT,
    ProjectPoolStatus.PENDING_GEOLOGY_VERIFY,
    ProjectPoolStatus.PENDING_PROCESS_VERIFY,
    ProjectPoolStatus.APPROVED,
    ProjectPoolStatus.DISPATCHED,
    ProjectPoolStatus.REJECTED,
]

HEATMAP_STATUSES = [
    ProjectPoolStatus.DRAFT,
    ProjectPoolStatus.PENDING_GEOLOGY_VERIFY,
    ProjectPoolStatus.PENDING_PROCESS_VERIFY,
    ProjectPoolStatus.APPROVED,
    ProjectPoolStatus.DISPATCHED,
    ProjectPoolStatus.REJECTED,
]


def _project_records(projects: list[WorkoverProjectPool]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for project in projects:
        measures = project.measures_jsonb.get("measures", []) if isinstance(project.measures_jsonb, dict) else []
        total_cost = sum(float(item.get("estimated_cost") or 0) for item in measures if isinstance(item, dict))
        records.append(
            {
                "id": project.id,
                "status": project.status.value,
                "block_name": project.block_name or "未填区块",
                "report_unit": project.report_unit,
                "production_priority": project.production_priority or 0,
                "created_at": project.created_at,
                "created_day": project.created_at.date() if project.created_at else None,
                "estimated_cost": total_cost,
                "measures": measures,
            }
        )
    return records


def _measure_records(projects: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if projects.empty:
        return records
    for row in projects.itertuples(index=False):
        for measure in getattr(row, "measures", []) or []:
            if isinstance(measure, dict) and measure.get("measure_type"):
                records.append(
                    {
                        "project_id": row.id,
                        "measure_type": str(measure["measure_type"]),
                        "estimated_cost": float(measure.get("estimated_cost") or 0),
                    }
                )
    return records


def _apply_analytics_dsl(projects: pd.DataFrame, query: WorkoverAnalyticsQuery) -> pd.DataFrame:
    if projects.empty:
        return projects
    filtered = projects.copy()
    if query.start_date:
        filtered = filtered[filtered["created_day"] >= query.start_date]
    if query.end_date:
        filtered = filtered[filtered["created_day"] <= query.end_date]
    if query.block_name:
        filtered = filtered[filtered["block_name"].str.contains(query.block_name, na=False)]
    if query.report_unit:
        filtered = filtered[filtered["report_unit"] == query.report_unit]
    if query.status:
        filtered = filtered[filtered["status"] == query.status.value]
    if query.measure_type:
        filtered = filtered[
            filtered["measures"].apply(
                lambda measures: any(
                    isinstance(item, dict) and query.measure_type in str(item.get("measure_type", ""))
                    for item in (measures or [])
                )
            )
        ]
    return filtered


def build_workover_analytics(
    db: Session,
    query: WorkoverAnalyticsQuery,
    *,
    scope: DataScope | None = None,
) -> WorkoverAnalyticsOut:
    stmt = select(WorkoverProjectPool).where(WorkoverProjectPool.is_deleted.is_(False))
    if scope is not None and not scope.is_global:
        stmt = stmt.where(reporting_unit_scope_predicate(scope))
    rows = list(db.scalars(stmt.order_by(WorkoverProjectPool.created_at.asc())).all())
    projects = pd.DataFrame(_project_records(rows))
    # Statistics supplies the scoped user's department as ``report_unit`` by
    # default.  That must not narrow a territory scope to reporting-unit rows:
    # the SQL scope above already admits either owned unit column.
    effective_query = query
    if scope is not None and not scope.is_global and query.report_unit == scope.department:
        effective_query = query.model_copy(update={"report_unit": None})
    filtered = _apply_analytics_dsl(projects, effective_query)
    measures = pd.DataFrame(_measure_records(filtered))

    total = int(len(filtered))
    pending = int(filtered["status"].isin([ProjectPoolStatus.PENDING_GEOLOGY_VERIFY.value, ProjectPoolStatus.PENDING_PROCESS_VERIFY.value]).sum()) if total else 0
    approved = int(filtered["status"].isin([ProjectPoolStatus.APPROVED.value, ProjectPoolStatus.DISPATCHED.value]).sum()) if total else 0
    estimated_cost = round(float(filtered["estimated_cost"].sum()), 2) if total else 0.0
    average_priority = round(float(filtered["production_priority"].mean()), 2) if total else 0.0

    status_counts = [
        StatusCountOut(
            status=status,
            label=STATUS_LABELS[status],
            count=int((filtered["status"] == status.value).sum()) if total else 0,
        )
        for status in STATUS_COUNT_ORDER
    ]

    if measures.empty:
        measure_distribution: list[NameValueOut] = []
        measure_types: list[str] = []
    else:
        measure_group = measures.groupby("measure_type").size().sort_values(ascending=False)
        measure_distribution = [NameValueOut(name=name, value=float(value)) for name, value in measure_group.items()]
        measure_types = sorted(measures["measure_type"].dropna().unique().tolist())

    blocks = sorted(filtered["block_name"].dropna().unique().tolist()) if total else []
    heatmap_data: list[tuple[int, int, float]] = []
    for x, block in enumerate(blocks):
        for y, status in enumerate(HEATMAP_STATUSES):
            value = filtered[(filtered["block_name"] == block) & (filtered["status"] == status.value)]["production_priority"].sum()
            heatmap_data.append((x, y, float(value)))

    if total:
        trend_group = filtered.groupby("created_day", dropna=True).agg(count=("id", "count"), cost=("estimated_cost", "sum")).sort_index()
        trend = TrendOut(
            days=[day.strftime("%m-%d") if isinstance(day, date) else str(day) for day in trend_group.index],
            counts=[int(value) for value in trend_group["count"].tolist()],
            costs=[round(float(value), 2) for value in trend_group["cost"].tolist()],
        )
    else:
        trend = TrendOut(days=[], counts=[], costs=[])

    return WorkoverAnalyticsOut(
        kpis=AnalyticsKpiOut(
            total_projects=total,
            pending_approvals=pending,
            approval_rate=round((approved / total) * 100, 2) if total else 0,
            estimated_cost=estimated_cost,
            average_priority=average_priority,
        ),
        status_counts=status_counts,
        measure_distribution=measure_distribution,
        heatmap=HeatmapOut(blocks=blocks, statuses=HEATMAP_STATUSES, data=heatmap_data),
        trend=trend,
        measure_types=measure_types,
    )
