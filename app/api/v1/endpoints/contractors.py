from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.crud.contractor import (
    confirm_contractor_capacity,
    create_contractor_capacity,
    dispatch_operation,
    get_contractor_capacity_for_user,
    get_contractor_overview,
    get_contractor_sync_summary,
    list_contractor_capacities,
    list_contractor_operation_sheets,
    list_contractor_sync_logs,
    mark_contractor_exception,
    resolve_contractor_exception,
    sync_contractor_capacities,
    update_contractor_capacity,
)
from app.db.session import get_db
from app.models.rbac import User
from app.services.data_scope_service import can_view_all_data
from app.core.exceptions import BusinessException
from app.core.status_codes import FORBIDDEN
from app.schemas.contractor import (
    ContractorCapacityCreate,
    ContractorCapacityOverview,
    ContractorCapacityOut,
    ContractorCapacityQuery,
    ContractorCapacitySyncLogOut,
    ContractorCapacitySyncLogQuery,
    ContractorCapacityUpdate,
    ContractorExceptionPayload,
    ContractorOperationSheetLinkOut,
    ContractorSyncPayload,
    ContractorSyncSummary,
    DispatchA5Out,
    DispatchPayload,
    ProgressPatch,
    WorkoverOperationSheetCreate,
    WorkoverOperationSheetOut,
    WorkoverOperationSheetQuery,
)
from app.schemas.pagination import PageResult
from app.schemas.response import ApiResponse, success
from app.services.a5_auth_service import generate_sso_token
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
    current_user: User = Depends(require_permission("contractor:read")),
) -> ApiResponse[PageResult[ContractorCapacityOut]]:
    rows, total = list_contractor_capacities(db, query, current_user=current_user)
    items = [ContractorCapacityOut.model_validate(row) for row in rows]
    return success(
        PageResult(items=items, total=total, page=query.page, page_size=query.page_size)
    )


@router.get("/sync-summary", response_model=ApiResponse[ContractorSyncSummary])
def sync_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:read")),
) -> ApiResponse[ContractorSyncSummary]:
    if not can_view_all_data(current_user):
        raise BusinessException(FORBIDDEN, "无权查看全局同步摘要")
    return success(ContractorSyncSummary(**get_contractor_sync_summary(db)))


@router.get("/overview", response_model=ApiResponse[ContractorCapacityOverview])
def capacity_overview(
    report_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:read")),
) -> ApiResponse[ContractorCapacityOverview]:
    return success(ContractorCapacityOverview(**get_contractor_overview(db, report_date=report_date, current_user=current_user)))


@router.post("/sync", response_model=ApiResponse[ContractorCapacitySyncLogOut])
def sync_capacities(
    payload: ContractorSyncPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:update")),
) -> ApiResponse[ContractorCapacitySyncLogOut]:
    from datetime import date

    if not can_view_all_data(current_user):
        raise BusinessException(FORBIDDEN, "无权触发全量承包商运力同步")
    log = sync_contractor_capacities(
        db,
        report_date=payload.report_date or datetime.now(ZoneInfo("Asia/Shanghai")).date(),
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
    )
    return success(ContractorCapacitySyncLogOut.model_validate(log), msg="同步完成")


@router.get("/sync-logs", response_model=ApiResponse[PageResult[ContractorCapacitySyncLogOut]])
def sync_logs(
    query: ContractorCapacitySyncLogQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:read")),
) -> ApiResponse[PageResult[ContractorCapacitySyncLogOut]]:
    if not can_view_all_data(current_user):
        raise BusinessException(FORBIDDEN, "无权查看全局同步日志")
    rows, total = list_contractor_sync_logs(db, query)
    items = [ContractorCapacitySyncLogOut.model_validate(row) for row in rows]
    return success(PageResult(items=items, total=total, page=query.page, page_size=query.page_size))


@router.post("/", response_model=ApiResponse[ContractorCapacityOut])
def create_item(
    payload: ContractorCapacityCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:create")),
) -> ApiResponse[ContractorCapacityOut]:
    obj = create_contractor_capacity(
        db, payload, operator_id=current_user.id, operator_ip=_client_ip(request), current_user=current_user
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
        current_user=current_user,
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
        current_user=current_user,
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
        db, payload, operator_id=current_user.id, operator_ip=_client_ip(request), current_user=current_user
    )
    return success(sheet, msg="工单创建成功")


@router.get("/operation-sheets/{sheet_id}", response_model=ApiResponse[WorkoverOperationSheetOut])
def sheet_detail(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("operation-sheet:read")),
) -> ApiResponse[WorkoverOperationSheetOut]:
    return success(get_workover_operation_sheet(db, sheet_id, current_user=current_user))


@router.patch("/dispatch", response_model=ApiResponse[DispatchA5Out])
def dispatch(
    payload: DispatchPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("operation-sheet:dispatch")),
) -> ApiResponse[DispatchA5Out]:
    """分配上修队伍，并返回 A5 措施审核跳转地址。"""
    sheet = dispatch_operation(
        db,
        payload.operation_sheet_id,
        payload.contractor_capacity_id,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
        current_user=current_user,
    )
    token = generate_sso_token(
        sheet.project_well_no or sheet.operation_no,
        payload.redirect_path,
        operation_no=sheet.operation_no,
    )
    return success(
        DispatchA5Out(
            sheet=WorkoverOperationSheetOut.model_validate(sheet),
            redirect_url=token.redirect_url,
            token=token.token,
            expire_at=token.expire_at,
        ),
        msg="已分配队伍，请在 A5 完成措施审核及下发",
    )


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
        db,
        sheet_id,
        payload,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
        current_user=current_user,
    )
    return success(sheet, msg="进度已更新")


@router.get("/analytics/summary", response_model=ApiResponse[dict])
def operation_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("operation-sheet:read")),
) -> ApiResponse[dict]:
    """修井运行基础统计：运行状态分布、派工完成率、队伍工作量、措施类型分布。"""
    return success(build_workover_operation_dashboard(db, current_user=current_user))


@router.get("/{contractor_id}", response_model=ApiResponse[ContractorCapacityOut])
def detail(
    contractor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:read")),
) -> ApiResponse[ContractorCapacityOut]:
    return success(ContractorCapacityOut.model_validate(get_contractor_capacity_for_user(db, contractor_id, current_user)))


@router.post("/{contractor_id}/sync", response_model=ApiResponse[ContractorCapacitySyncLogOut])
def sync_one_capacity(
    contractor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:update")),
) -> ApiResponse[ContractorCapacitySyncLogOut]:
    from app.models.workover import ContractorCapacitySyncType

    obj = get_contractor_capacity_for_user(db, contractor_id, current_user, require_manage=True)
    if not obj.external_system_id:
        from app.core.status_codes import BAD_REQUEST

        raise BusinessException(BAD_REQUEST, "本地补录记录没有外部系统ID，不能单队伍重试")
    log = sync_contractor_capacities(
        db,
        report_date=obj.report_date,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
        sync_type=ContractorCapacitySyncType.SINGLE_TEAM,
        external_system_id=obj.external_system_id,
    )
    return success(ContractorCapacitySyncLogOut.model_validate(log), msg="单队伍重新拉取完成")


@router.patch("/{contractor_id}/confirm", response_model=ApiResponse[ContractorCapacityOut])
def confirm_capacity(
    contractor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:update")),
) -> ApiResponse[ContractorCapacityOut]:
    obj = confirm_contractor_capacity(db, contractor_id, operator_id=current_user.id, operator_ip=_client_ip(request), current_user=current_user)
    return success(ContractorCapacityOut.model_validate(obj), msg="已确认同步")


@router.patch("/{contractor_id}/exception", response_model=ApiResponse[ContractorCapacityOut])
def mark_exception(
    contractor_id: int,
    payload: ContractorExceptionPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:update")),
) -> ApiResponse[ContractorCapacityOut]:
    obj = mark_contractor_exception(
        db,
        contractor_id,
        reason=payload.reason,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
        current_user=current_user,
    )
    return success(ContractorCapacityOut.model_validate(obj), msg="已标记异常")


@router.patch("/{contractor_id}/resolve-exception", response_model=ApiResponse[ContractorCapacityOut])
def resolve_exception(
    contractor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:update")),
) -> ApiResponse[ContractorCapacityOut]:
    obj = resolve_contractor_exception(db, contractor_id, operator_id=current_user.id, operator_ip=_client_ip(request), current_user=current_user)
    return success(ContractorCapacityOut.model_validate(obj), msg="异常已解除")


@router.get("/{contractor_id}/operation-sheets", response_model=ApiResponse[list[ContractorOperationSheetLinkOut]])
def linked_operation_sheets(
    contractor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("operation-sheet:read")),
) -> ApiResponse[list[ContractorOperationSheetLinkOut]]:
    return success([ContractorOperationSheetLinkOut(**item) for item in list_contractor_operation_sheets(db, contractor_id, current_user=current_user)])


@router.put("/{contractor_id}", response_model=ApiResponse[ContractorCapacityOut])
def update_item(
    contractor_id: int,
    payload: ContractorCapacityUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contractor:update")),
) -> ApiResponse[ContractorCapacityOut]:
    obj = update_contractor_capacity(
        db,
        contractor_id,
        payload,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
        current_user=current_user,
    )
    return success(ContractorCapacityOut.model_validate(obj), msg="更新成功")
