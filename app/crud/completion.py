from datetime import date
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST
from app.models.completion import WellCompletionRecord
from app.schemas.completion import WellCompletionCreate, WellCompletionQuery, WellCompletionUpdate


def _apply_filters(stmt: Select[tuple[WellCompletionRecord]], query: WellCompletionQuery) -> Select[tuple[WellCompletionRecord]]:
    if query.well_no:
        stmt = stmt.where(WellCompletionRecord.well_no.ilike(f"%{query.well_no}%"))
    if query.measure_type:
        stmt = stmt.where(WellCompletionRecord.measure_type == query.measure_type)
    if query.start_date:
        stmt = stmt.where(WellCompletionRecord.completion_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(WellCompletionRecord.completion_date <= query.end_date)
    return stmt


def list_completion_records(db: Session, query: WellCompletionQuery) -> tuple[list[WellCompletionRecord], int]:
    base_stmt = _apply_filters(select(WellCompletionRecord), query)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    rows = db.scalars(
        base_stmt.order_by(WellCompletionRecord.completion_date.desc().nullslast(), WellCompletionRecord.created_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return list(rows), total


def get_completion_record(db: Session, record_id: int) -> WellCompletionRecord:
    obj = db.get(WellCompletionRecord, record_id)
    if obj is None:
        raise BusinessException(BAD_REQUEST, "完井记录不存在")
    return obj


def create_completion_record(db: Session, payload: WellCompletionCreate) -> WellCompletionRecord:
    data = payload.model_dump(mode="json")
    obj = WellCompletionRecord(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_completion_record(db: Session, record_id: int, payload: WellCompletionUpdate) -> WellCompletionRecord:
    obj = get_completion_record(db, record_id)
    data = payload.model_dump(mode="json", exclude_unset=True)
    for key, value in data.items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_completion_record(db: Session, record_id: int) -> None:
    obj = get_completion_record(db, record_id)
    db.delete(obj)
    db.commit()


def get_completion_analytics(db: Session) -> dict[str, Any]:
    """完井分类统计：按措施类型分组统计。"""
    rows = db.scalars(select(WellCompletionRecord)).all()
    by_type: dict[str, int] = {}
    for row in rows:
        by_type[row.measure_type] = by_type.get(row.measure_type, 0) + 1
    return {
        "total": len(rows),
        "by_measure_type": [{"measure_type": k, "count": v} for k, v in sorted(by_type.items(), key=lambda x: -x[1])],
    }
