import json

from sqlalchemy import Boolean, Integer, inspect, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

from app.db.base import Base


def _sqlite_literal(value) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (dict, list)):
        return "'" + json.dumps(value, ensure_ascii=False).replace("'", "''") + "'"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def _default_for_column(column):
    if column.default is not None:
        arg = column.default.arg
        if callable(arg):
            try:
                return arg()
            except TypeError:
                return arg(None)
        return arg
    if isinstance(column.type, JSONB):
        return {}
    if isinstance(column.type, Boolean):
        return False
    if isinstance(column.type, Integer):
        return 0
    return ""


def _sqlite_add_column_sql(engine: Engine, table_name: str, column) -> str:
    type_sql = column.type.compile(dialect=engine.dialect)
    sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {type_sql}'
    if not column.nullable:
        sql += f" NOT NULL DEFAULT {_sqlite_literal(_default_for_column(column))}"
    return sql


def ensure_sqlite_columns(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        for table in Base.metadata.sorted_tables:
            if table.name not in table_names:
                continue
            existing = {column["name"] for column in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing or column.primary_key:
                    continue
                conn.execute(text(_sqlite_add_column_sql(engine, table.name, column)))
