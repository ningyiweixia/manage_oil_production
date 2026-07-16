from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_any_permission, require_permission
from app.db.session import get_db
from app.core.exceptions import BusinessException
from app.core.status_codes import A5_LINK_FAILED
from app.models.rbac import User
from app.schemas.contractor import (
    ProgressPatch,
    WorkoverOperationSheetCreate,
    WorkoverOperationSheetQuery,
)
from app.schemas.pagination import PageResult
from app.schemas.response import ApiResponse, success
from app.schemas.a5_integration import A5SyncTriggerOut, A5TokenResponse
from app.services.a5_auth_service import generate_sso_token
from app.services.a5_sync_service import sync_daily_operations
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
    current_user: User = Depends(require_any_permission("workover_operation:read", "operation-sheet:read")),
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
    current_user: User = Depends(require_any_permission("workover_operation:read", "operation-sheet:read")),
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
    current_user: User = Depends(require_any_permission("workover_operation:create", "operation-sheet:create")),
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
    current_user: User = Depends(require_any_permission("workover_operation:read", "operation-sheet:read")),
) -> ApiResponse[dict]:
    return success(get_workover_operation_sheet(db, sheet_id, current_user=current_user))


@router.post("/sheets/{sheet_id}/a5-link", response_model=ApiResponse[A5TokenResponse])
def a5_link(
    sheet_id: int,
    redirect_path: str = "/measure-review",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("a5:sso")),
) -> ApiResponse[A5TokenResponse]:
    sheet = get_workover_operation_sheet(db, sheet_id, current_user=current_user)
    return success(
        generate_sso_token(
            sheet.get("project_well_no") or sheet["operation_no"],
            redirect_path,
            operation_no=sheet["operation_no"],
        )
    )


@router.post("/a5-sync", response_model=ApiResponse[A5SyncTriggerOut])
async def sync_all_sheets(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("workover_operation:a5_sync")),
) -> ApiResponse[A5SyncTriggerOut]:
    """立即同步全部修井运行表关联的 A5 日报。"""
    result = await sync_daily_operations(db, sync_type="MANUAL")
    if result.get("error"):
        raise BusinessException(A5_LINK_FAILED, str(result["error"]))
    return success(
        A5SyncTriggerOut(
            task_id="workover-manual",
            message=f"A5 日报同步完成，更新 {result.get('updated', 0)} 条，失败 {result.get('failed', 0)} 条",
            updated_count=result.get("updated", 0),
            failed_count=result.get("failed", 0),
        ),
        msg="A5 日报同步部分完成" if result.get("failed", 0) else "A5 日报同步完成",
    )


@router.post("/sheets/{sheet_id}/a5-sync", response_model=ApiResponse[A5SyncTriggerOut])
async def sync_single_sheet(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_operation:a5_sync")),
) -> ApiResponse[A5SyncTriggerOut]:
    sheet = get_workover_operation_sheet(db, sheet_id, current_user=current_user)
    result = await sync_daily_operations(
        db,
        operation_no=sheet["operation_no"],
        sync_type="SINGLE",
    )
    if result.get("error"):
        raise BusinessException(A5_LINK_FAILED, str(result["error"]))
    return success(
        A5SyncTriggerOut(
            task_id=f"single-{sheet_id}",
            message=f"A5同步完成，更新 {result.get('updated', 0)} 条，失败 {result.get('failed', 0)} 条",
            updated_count=result.get("updated", 0),
            failed_count=result.get("failed", 0),
        ),
        msg="A5同步部分完成" if result.get("failed", 0) else "A5同步完成",
    )


@router.patch("/sheets/{sheet_id}/progress", response_model=ApiResponse[dict])
def update_progress(
    sheet_id: int,
    payload: ProgressPatch,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_permission("workover_operation:update", "operation-sheet:update")),
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
    current_user: User = Depends(
        require_any_permission("workover_operation:dashboard", "workover_operation:read", "operation-sheet:read")
    ),
) -> ApiResponse[dict]:
    return success(build_workover_operation_dashboard(db, current_user=current_user))
