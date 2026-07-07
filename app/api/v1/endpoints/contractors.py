from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.crud.contractor import (
    create_contractor_capacity,
    dispatch_operation,
    get_contractor_capacity,
    list_contractor_capacities,
    update_contractor_capacity,
)
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.contractor import (
    ContractorCapacityCreate,
    ContractorCapacityOut,
    ContractorCapacityQuery,
    ContractorCapacityUpdate,
    DispatchPayload,
    ProgressPatch,
    WorkoverOperationSheetCreate,
    WorkoverOperationSheetOut,
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

router = APIRouter(prefix="/contractors", tags=["承包商管理"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/", response_model=ApiResponse[PageResult[ContractorCapacityOut]])
def list_items(
    query: ContractorCapacityQuery = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contractor:read")),
) -> ApiResponse[PageResult[ContractorCapacityOut]]:
    rows, total = list_contractor_capacities(db, query)
    items = [ContractorCapacityOut.model_validate(row) for row in rows]
    return success(
        PageResult(items=items, total=total, page=query.page, page_size=query.page_size)
    )


@router.post("/", response_model=ApiResponse[ContractorCapacityOut])
def create_item(
    payload: ContractorCapacityCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:create")),
) -> ApiResponse[ContractorCapacityOut]:
    obj = create_contractor_capacity(
        db, payload, operator_id=current_user.id, operator_ip=_client_ip(request)
    )
    return success(ContractorCapacityOut.model_validate(obj), msg="报备成功")


@router.get("/priority-sheets", response_model=ApiResponse[list[WorkoverOperationSheetOut]])
def list_priority_sheets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("operation-sheet:read")),
) -> ApiResponse[list[WorkoverOperationSheetOut]]:
    """按优先级排序的待派工修井运行表。"""
    items = list_priority_operation_sheets(
        db,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
    )
    return success(items)


@router.get("/operation-sheets/", response_model=ApiResponse[PageResult[WorkoverOperationSheetOut]])
def list_sheets(
    request: Request,
    query: WorkoverOperationSheetQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("operation-sheet:read")),
) -> ApiResponse[PageResult[dict]]:
    rows, total = list_workover_operation_sheets(
        db,
        query,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
    )
    return success(
        PageResult(items=rows, total=total, page=query.page, page_size=query.page_size)
    )


@router.post("/operation-sheets/", response_model=ApiResponse[WorkoverOperationSheetOut])
def create_sheet(
    payload: WorkoverOperationSheetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("operation-sheet:create")),
) -> ApiResponse[WorkoverOperationSheetOut]:
    sheet = create_workover_operation_sheet(
        db, payload, operator_id=current_user.id, operator_ip=_client_ip(request)
    )
    return success(sheet, msg="工单创建成功")


@router.get("/operation-sheets/{sheet_id}", response_model=ApiResponse[WorkoverOperationSheetOut])
def sheet_detail(
    sheet_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("operation-sheet:read")),
) -> ApiResponse[WorkoverOperationSheetOut]:
    return success(get_workover_operation_sheet(db, sheet_id))


@router.patch("/dispatch", response_model=ApiResponse[WorkoverOperationSheetOut])
def dispatch(
    payload: DispatchPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("operation-sheet:dispatch")),
) -> ApiResponse[WorkoverOperationSheetOut]:
    """分配队伍（核心派工接口），含 Redis 分布式锁防重机制。"""
    sheet = dispatch_operation(
        db,
        payload.operation_sheet_id,
        payload.contractor_capacity_id,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
    )
    return success(WorkoverOperationSheetOut.model_validate(sheet), msg="派工成功")


@router.patch("/operation-sheets/{sheet_id}/progress", response_model=ApiResponse[WorkoverOperationSheetOut])
def update_progress(
    sheet_id: int,
    payload: ProgressPatch,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("operation-sheet:update")),
) -> ApiResponse[WorkoverOperationSheetOut]:
    """更新施工进度，进度到达 100% 自动推进工单状态。"""
    sheet = update_workover_operation_progress(
        db, sheet_id, payload, operator_id=current_user.id, operator_ip=_client_ip(request)
    )
    return success(sheet, msg="进度已更新")


@router.get("/analytics/summary", response_model=ApiResponse[dict])
def operation_analytics(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("operation-sheet:read")),
) -> ApiResponse[dict]:
    """修井运行基础统计：运行状态分布、派工完成率、队伍工作量、措施类型分布。"""
    return success(build_workover_operation_dashboard(db))


@router.get("/{contractor_id}", response_model=ApiResponse[ContractorCapacityOut])
def detail(
    contractor_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contractor:read")),
) -> ApiResponse[ContractorCapacityOut]:
    return success(ContractorCapacityOut.model_validate(get_contractor_capacity(db, contractor_id)))


@router.put("/{contractor_id}", response_model=ApiResponse[ContractorCapacityOut])
def update_item(
    contractor_id: int,
    payload: ContractorCapacityUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:update")),
) -> ApiResponse[ContractorCapacityOut]:
    obj = update_contractor_capacity(
        db, contractor_id, payload, operator_id=current_user.id, operator_ip=_client_ip(request)
    )
    return success(ContractorCapacityOut.model_validate(obj), msg="更新成功")
