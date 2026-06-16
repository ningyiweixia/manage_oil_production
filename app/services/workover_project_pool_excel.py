import base64
from io import BytesIO
from uuid import uuid4

import pandas as pd

from app.schemas.workover_project_pool import ImportTaskOut, WorkoverProjectPoolCreate


REQUIRED_COLUMNS = {
    "well_no",
    "report_unit",
}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
FORMULA_PREFIXES = ("=", "+", "-", "@")


def _sanitize_cell(value):
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value


def parse_project_pool_excel(content: bytes) -> list[WorkoverProjectPoolCreate]:
    if len(content) > MAX_UPLOAD_SIZE:
        raise ValueError("Excel file is too large; max size is 10MB")
    frame = pd.read_excel(BytesIO(content), engine="openpyxl")
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Excel模板缺少字段: {sorted(missing)}")

    records = frame.where(pd.notna(frame), None).to_dict(orient="records")
    return [WorkoverProjectPoolCreate.model_validate(record) for record in records]


def export_project_pool_excel(rows: list[dict]) -> dict[str, str]:
    output = BytesIO()
    frame = pd.DataFrame(rows).map(_sanitize_cell)
    frame.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    return {
        "filename": "workover_project_pool.xlsx",
        "content_base64": base64.b64encode(output.read()).decode("ascii"),
    }


def enqueue_import_workover_project_pool(_: bytes) -> ImportTaskOut:
    # Celery hook placeholder: replace with celery_app.send_task(...) when the
    # distributed task module is introduced.
    return ImportTaskOut(task_id=f"local-{uuid4().hex}", status="LOCAL_EXECUTED")
