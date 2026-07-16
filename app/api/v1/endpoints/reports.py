from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.response import ApiResponse, success
from app.services.report_service import (
    build_delivery_summary,
    export_delivery_summary_excel,
    export_delivery_summary_word,
    export_statistics_analysis_excel,
    export_statistics_analysis_word,
)
from app.services.statistics_analysis_service import StatisticsAnalysisQuery, build_statistics_analysis
from app.services.data_scope_service import build_data_scope

router = APIRouter(prefix="/reports", tags=["报表交付"])


@router.get("/delivery-summary", response_model=ApiResponse[dict])
def delivery_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:read")),
) -> ApiResponse[dict]:
    return success(build_delivery_summary(db, scope=build_data_scope(current_user)))


@router.get("/statistics-analysis", response_model=ApiResponse[dict])
def statistics_analysis(
    query: StatisticsAnalysisQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:read")),
) -> ApiResponse[dict]:
    return success(build_statistics_analysis(db, query, scope=build_data_scope(current_user)))


@router.get("/delivery-summary.xlsx")
def delivery_summary_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:export")),
) -> Response:
    content = export_delivery_summary_excel(db, scope=build_data_scope(current_user))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="delivery-summary.xlsx"'},
    )


@router.get("/delivery-summary.docx")
def delivery_summary_word(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:export")),
) -> Response:
    content = export_delivery_summary_word(db, scope=build_data_scope(current_user))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="delivery-summary.docx"'},
    )


@router.get("/statistics-analysis.xlsx")
def statistics_analysis_excel(
    query: StatisticsAnalysisQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:export")),
) -> Response:
    content = export_statistics_analysis_excel(db, query, scope=build_data_scope(current_user))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="statistics-analysis.xlsx"'},
    )


@router.get("/statistics-analysis.docx")
def statistics_analysis_word(
    query: StatisticsAnalysisQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:export")),
) -> Response:
    content = export_statistics_analysis_word(db, query, scope=build_data_scope(current_user))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="statistics-analysis.docx"'},
    )
