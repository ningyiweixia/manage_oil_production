import base64
from io import BytesIO
from uuid import uuid4

from openpyxl import Workbook
from openpyxl.styles import Font
import pandas as pd

from app.schemas.workover_project_pool import ImportTaskOut, WorkoverProjectPoolCreate


REQUIRED_COLUMNS = {
    "well_no",
    "report_unit",
    "reason_category",
    "measure_type",
}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
FORMULA_PREFIXES = ("=", "+", "-", "@")
ALLOWED_MEASURE_TYPES = {
    "pump_repair",
    "pump_inspection",
    "sand_washing",
    "acidizing",
    "tubing_replacement",
    "major_workover",
    "hot_wax_washing",
    "casing_damage_treatment",
}
TEMPLATE_COLUMNS = [
    "well_no",
    "well_name",
    "well_type",
    "layer",
    "fault_description",
    "territory_unit",
    "block_name",
    "county",
    "report_unit",
    "initiator_name",
    "initiator_phone",
    "production_priority",
    "reason",
    "reason_category",
    "completeness_status",
    "data_source",
    "report_batch",
    "photo_requirement",
    "measure_type",
    "process",
    "duration_days",
    "estimated_cost",
    "photo_urls",
    "remark",
]


def _sanitize_cell(value):
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value


def _string_or_none(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_urls(value) -> list[str]:
    text = _string_or_none(value)
    if not text:
        return []
    return [item.strip() for item in text.replace("；", ",").replace(";", ",").split(",") if item.strip()]


def _row_to_payload(record: dict) -> dict:
    measure_type = _string_or_none(record.get("measure_type"))
    return {
        "well_no": _string_or_none(record.get("well_no")),
        "well_name": _string_or_none(record.get("well_name")),
        "well_type": _string_or_none(record.get("well_type")),
        "layer": _string_or_none(record.get("layer")),
        "fault_description": _string_or_none(record.get("fault_description")),
        "territory_unit": _string_or_none(record.get("territory_unit")),
        "block_name": _string_or_none(record.get("block_name")),
        "county": _string_or_none(record.get("county")),
        "report_unit": _string_or_none(record.get("report_unit")),
        "initiator_name": _string_or_none(record.get("initiator_name")),
        "initiator_phone": _string_or_none(record.get("initiator_phone")),
        "production_priority": int(record.get("production_priority") or 0),
        "reason": _string_or_none(record.get("reason")),
        "reason_category": _string_or_none(record.get("reason_category")),
        "completeness_status": _string_or_none(record.get("completeness_status")) or "INCOMPLETE",
        "data_source": _string_or_none(record.get("data_source")) or "excel",
        "report_batch": _string_or_none(record.get("report_batch")),
        "photo_requirement": _string_or_none(record.get("photo_requirement")),
        "measures_jsonb": {
            "measures": [
                {
                    "measure_type": measure_type,
                    "process": _string_or_none(record.get("process")),
                    "construction_params": {},
                    "duration_days": int(record.get("duration_days") or 0),
                    "estimated_cost": record.get("estimated_cost") or 0,
                }
            ]
        },
        "photo_urls": _split_urls(record.get("photo_urls")),
        "attachments": [
            {
                "name": url.rsplit("/", 1)[-1] or "导入照片",
                "url": url,
                "content_type": "image/jpeg",
                "size": 0,
                "category": "imported",
            }
            for url in _split_urls(record.get("photo_urls"))
        ],
        "remark": _string_or_none(record.get("remark")),
    }


def export_project_pool_template() -> dict[str, str]:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "项目池导入模板"
    sheet.append(TEMPLATE_COLUMNS)
    sheet.append(
        [
            "CY2-001",
            "采二-001",
            "油井",
            "长6",
            "产液下降，检泵周期缩短",
            "采油一队",
            "北一区",
            "红岗区",
            "采油一队",
            "张三",
            "13800000001",
            80,
            "产量核实后建议优先安排",
            "产量下降",
            "COMPLETE",
            "excel",
            "202607-A",
            "需上传井口、井场、故障照片",
            "pump_inspection",
            "起泵检查",
            3,
            7.8,
            "https://example.local/photo.jpg",
            "示例行可删除",
        ]
    )
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    instruction = workbook.create_sheet("填写说明")
    instruction.append(["字段", "说明"])
    instruction.append(["well_no/report_unit/reason_category/measure_type", "必填字段"])
    instruction.append(["measure_type", f"允许值：{', '.join(sorted(ALLOWED_MEASURE_TYPES))}"])
    instruction.append(["completeness_status", "INCOMPLETE、COMPLETE、NEEDS_SUPPLEMENT"])
    instruction.append(["data_source", "manual、excel、external；导入默认 excel"])
    instruction.append(["photo_urls", "多个照片地址用逗号或分号分隔"])
    for cell in instruction[1]:
        cell.font = Font(bold=True)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return {
        "filename": "workover_project_pool_import_template.xlsx",
        "content_base64": base64.b64encode(output.read()).decode("ascii"),
    }


def parse_project_pool_excel(content: bytes) -> list[WorkoverProjectPoolCreate]:
    if len(content) > MAX_UPLOAD_SIZE:
        raise ValueError("Excel file is too large; max size is 10MB")
    frame = pd.read_excel(BytesIO(content), engine="openpyxl")
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Excel模板缺少字段: {sorted(missing)}")

    records = frame.where(pd.notna(frame), None).to_dict(orient="records")
    errors: list[str] = []
    seen_well_nos: set[str] = set()
    parsed: list[WorkoverProjectPoolCreate] = []
    for index, record in enumerate(records, start=2):
        row_errors: list[str] = []
        well_no = _string_or_none(record.get("well_no"))
        measure_type = _string_or_none(record.get("measure_type"))
        if well_no in seen_well_nos:
            row_errors.append(f"重复井号 {well_no}")
        if well_no:
            seen_well_nos.add(well_no)
        if measure_type not in ALLOWED_MEASURE_TYPES:
            row_errors.append(f"measure_type 不在允许范围: {measure_type}")
        try:
            payload = WorkoverProjectPoolCreate.model_validate(_row_to_payload(record))
        except Exception as exc:
            row_errors.append(str(exc))
            payload = None
        if row_errors:
            errors.append(f"第{index}行: " + "；".join(row_errors))
            continue
        if payload is not None:
            parsed.append(payload)
    if errors:
        raise ValueError("\n".join(errors))
    return parsed


EXPORT_COLUMN_MAP: dict[str, str] = {
    "well_no": "井号",
    "well_type": "井别",
    "block_name": "区块",
    "report_unit": "提报单位",
    "reason_category": "原因分类",
    "report_batch": "提报批次",
    "completeness_status": "资料完整性",
    "is_duplicate_well": "重复井",
    "status": "状态",
    "initiator_name": "提报人",
    "created_at": "创建时间",
}


def export_project_pool_excel(rows: list[dict]) -> dict[str, str]:
    output = BytesIO()
    if not rows:
        frame = pd.DataFrame(columns=list(EXPORT_COLUMN_MAP.values()))
    else:
        frame = pd.DataFrame(rows).map(_sanitize_cell)
        frame = frame[[col for col in EXPORT_COLUMN_MAP if col in frame.columns]]
        frame.columns = [EXPORT_COLUMN_MAP[col] for col in frame.columns]
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
