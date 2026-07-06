from io import BytesIO
from typing import Any

from docx import Document
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.crud.completion import get_completion_analytics
from app.crud.contractor import get_operation_analytics
from app.crud.material import get_material_analytics
from app.schemas.workover_project_pool import WorkoverAnalyticsQuery
from app.services.workover_analytics_service import build_workover_analytics


def build_delivery_summary(db: Session) -> dict[str, Any]:
    workover = build_workover_analytics(db, WorkoverAnalyticsQuery())
    operations = get_operation_analytics(db)
    materials = get_material_analytics(db)
    completions = get_completion_analytics(db)

    return {
        "projects": {
            "total": workover.kpis.total_projects,
            "pending_approvals": workover.kpis.pending_approvals,
            "approval_rate": workover.kpis.approval_rate,
            "estimated_cost": workover.kpis.estimated_cost,
        },
        "operations": {
            "total_sheets": operations.get("total_sheets", 0),
            "dispatch_rate": operations.get("dispatch_rate", 0),
            "completion_rate": operations.get("completion_rate", 0),
            "team_workload": operations.get("team_workload", []),
        },
        "materials": {
            "total": materials.get("total", 0),
            "delivered": materials.get("delivered", 0),
            "arrived": materials.get("arrived", 0),
            "used": materials.get("used", 0),
            "emergency_count": materials.get("emergency_count", 0),
        },
        "completions": {
            "total": completions.get("total", 0),
            "by_measure_type": completions.get("by_measure_type", []),
        },
    }


def export_delivery_summary_excel(db: Session) -> bytes:
    summary = build_delivery_summary(db)
    wb = Workbook()
    ws = wb.active
    ws.title = "试运行验收摘要"
    ws.append(["模块", "指标", "值"])
    rows = [
        ("项目池", "项目总数", summary["projects"]["total"]),
        ("项目池", "待审批", summary["projects"]["pending_approvals"]),
        ("项目池", "通过率", summary["projects"]["approval_rate"]),
        ("运行表", "工单总数", summary["operations"]["total_sheets"]),
        ("运行表", "派工率", summary["operations"]["dispatch_rate"]),
        ("运行表", "完工率", summary["operations"]["completion_rate"]),
        ("物料", "需求总数", summary["materials"]["total"]),
        ("物料", "紧急需求", summary["materials"]["emergency_count"]),
        ("完井", "完井记录", summary["completions"]["total"]),
    ]
    for row in rows:
        ws.append(row)
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def export_delivery_summary_word(db: Session) -> bytes:
    summary = build_delivery_summary(db)
    doc = Document()
    doc.add_heading("采油二厂井下作业管理系统试运行验收摘要", level=1)
    doc.add_paragraph(f"项目池总数：{summary['projects']['total']}")
    doc.add_paragraph(f"待审批项目：{summary['projects']['pending_approvals']}")
    doc.add_paragraph(f"运行表工单总数：{summary['operations']['total_sheets']}")
    doc.add_paragraph(f"物料需求总数：{summary['materials']['total']}")
    doc.add_paragraph(f"完井记录总数：{summary['completions']['total']}")
    output = BytesIO()
    doc.save(output)
    return output.getvalue()
