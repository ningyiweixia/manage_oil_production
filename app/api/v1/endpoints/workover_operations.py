from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.contractor import (
    ProgressPatch,
    WorkoverOperationSheetCreate,
    WorkoverOperationSheetQuery,
)
from app.schemas.pagination import PageResult
from app.schemas.response import ApiResponse, success
from app.services.workover_operation_service import (
    build_workover_operation_dashboard,
    create_workover_operation_sheet,
    get_workover_operation_sheet,
    list_priority_operation_sheets,
    list_workover_operation_sheets,
    update_workover_operation_progress,
)

router = APIRouter(prefix="/workover-operations", tags=["修井运行管理"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/sheets/", response_model=ApiResponse[PageResult[dict]])
def list_sheets(
    request: Request,
    query: WorkoverOperationSheetQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_operation:read")),
) -> ApiResponse[PageResult[dict]]:
    rows, total = list_workover_operation_sheets(
        db,
        query,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
        current_user=current_user,
    )
    return success(PageResult(items=rows, total=total, page=query.page, page_size=query.page_size))


@router.get("/priority-sheets", response_model=ApiResponse[list[dict]])
def priority_sheets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_operation:read")),
) -> ApiResponse[list[dict]]:
    return success(
        list_priority_operation_sheets(
            db,
            operator_id=current_user.id,
            operator_ip=_client_ip(request),
            current_user=current_user,
        )
    )


@router.post("/sheets/", response_model=ApiResponse[dict])
def create_sheet(
    payload: WorkoverOperationSheetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_operation:create")),
) -> ApiResponse[dict]:
    return success(
        create_workover_operation_sheet(
            db,
            payload,
            operator_id=current_user.id,
            operator_ip=_client_ip(request),
            current_user=current_user,
        ),
        msg="运行表创建成功",
    )


@router.get("/sheets/{sheet_id}", response_model=ApiResponse[dict])
def sheet_detail(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_operation:read")),
) -> ApiResponse[dict]:
    return success(get_workover_operation_sheet(db, sheet_id, current_user=current_user))


@router.patch("/sheets/{sheet_id}/progress", response_model=ApiResponse[dict])
def update_progress(
    sheet_id: int,
    payload: ProgressPatch,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_operation:update")),
) -> ApiResponse[dict]:
    return success(
        update_workover_operation_progress(
            db,
            sheet_id,
            payload,
            operator_id=current_user.id,
            operator_ip=_client_ip(request),
            current_user=current_user,
        ),
        msg="进度已更新",
    )


@router.get("/dashboard", response_model=ApiResponse[dict])
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_operation:dashboard")),
) -> ApiResponse[dict]:
    return success(build_workover_operation_dashboard(db, current_user=current_user))
