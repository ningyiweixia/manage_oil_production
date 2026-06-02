from typing import Any

from sqlalchemy.sql.elements import ColumnElement


def jsonb_contains(column: Any, payload: dict[str, Any]) -> ColumnElement[bool]:
    """Build a PostgreSQL JSONB containment condition; compiles to the native @> operator."""

    return column.contains(payload)


def measure_type_filter(column: Any, measure_type: str) -> ColumnElement[bool]:
    return jsonb_contains(column, {"measures": [{"measure_type": measure_type}]})
