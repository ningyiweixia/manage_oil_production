from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST
from app.crud.workover_project_pool import (
    create_project_pool,
    delete_project_pool,
    get_project_pool,
    list_all_project_pools,
    list_project_pools,
    patch_project_status,
    submit_project_pools,
    update_project_pool,
)
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.pagination import PageResult
from app.schemas.response import ApiResponse, success
from app.schemas.workover_project_pool import (
    ImportTaskOut,
    WorkoverProjectPoolCreate,
    WorkoverProjectPoolOut,
    WorkoverProjectPoolQuery,
    WorkoverProjectPoolStatusPatch,
    WorkoverProjectPoolSubmit,
    WorkoverProjectPoolUpdate,
)
from app.services.notification_service import push_geology_todo, push_status_changed
from app.services.workover_project_pool_excel import (
    enqueue_import_workover_project_pool,
    export_project_pool_excel,
    parse_project_pool_excel,
)

router = APIRouter(prefix="/workover-project-pools", tags=["上修项目池"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/", response_model=ApiResponse[PageResult[WorkoverProjectPoolOut]])
def list_items(
    query: WorkoverProjectPoolQuery = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("workover_project_pool:read")),
) -> ApiResponse[PageResult[WorkoverProjectPoolOut]]:
    rows, total = list_project_pools(db, query)
    return success(
        PageResult(
            items=[WorkoverProjectPoolOut.model_validate(row) for row in rows],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
    )


@router.post("/import", response_model=ApiResponse[ImportTaskOut])
def import_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_project_pool:import")),
) -> ApiResponse[ImportTaskOut]:
    content = file.file.read()
    task = enqueue_import_workover_project_pool(content)
    try:
        rows = parse_project_pool_excel(content)
    except ValueError as exc:
        raise BusinessException(BAD_REQUEST, str(exc)) from exc
    imported_count = 0
    for row in rows:
        create_project_pool(
            db,
            row,
            operator_id=current_user.id,
            operator_ip=_client_ip(request),
        )
        imported_count += 1
    task.imported_count = imported_count
    return success(task, msg="导入成功")


@router.get("/export/all", response_model=ApiResponse[dict[str, str]])
def export_all(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("workover_project_pool:export")),
) -> ApiResponse[dict[str, str]]:
    payload = [
        WorkoverProjectPoolOut.model_validate(row).model_dump(mode="json")
        for row in list_all_project_pools(db)
    ]
    return success(export_project_pool_excel(payload), msg="导出成功")


@router.get("/{project_id}", response_model=ApiResponse[WorkoverProjectPoolOut])
def detail(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("workover_project_pool:read")),
) -> ApiResponse[WorkoverProjectPoolOut]:
    return success(WorkoverProjectPoolOut.model_validate(get_project_pool(db, project_id)))


@router.post("/", response_model=ApiResponse[WorkoverProjectPoolOut])
def create_item(
    payload: WorkoverProjectPoolCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_project_pool:create")),
) -> ApiResponse[WorkoverProjectPoolOut]:
    project = create_project_pool(
        db,
        payload,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
    )
    return success(WorkoverProjectPoolOut.model_validate(project), msg="创建成功")


@router.put("/{project_id}", response_model=ApiResponse[WorkoverProjectPoolOut])
def update_item(
    project_id: int,
    payload: WorkoverProjectPoolUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_project_pool:update")),
) -> ApiResponse[WorkoverProjectPoolOut]:
    project = update_project_pool(
        db,
        project_id,
        payload,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
    )
    return success(WorkoverProjectPoolOut.model_validate(project), msg="更新成功")


@router.patch("/submit", response_model=ApiResponse[list[WorkoverProjectPoolOut]])
async def submit_items(
    payload: WorkoverProjectPoolSubmit,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_project_pool:submit")),
) -> ApiResponse[list[WorkoverProjectPoolOut]]:
    projects = submit_project_pools(
        db,
        payload.project_ids,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
        comment=payload.comment,
    )
    await push_geology_todo(
        {
            "node_code": "PENDING_GEOLOGY_VERIFY",
            "project_ids": [project.id for project in projects],
            "well_nos": [project.well_no for project in projects],
        }
    )
    return success([WorkoverProjectPoolOut.model_validate(project) for project in projects], msg="提报成功")


@router.patch("/{project_id}/status", response_model=ApiResponse[WorkoverProjectPoolOut])
async def patch_status(
    project_id: int,
    payload: WorkoverProjectPoolStatusPatch,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_project_pool:approve")),
) -> ApiResponse[WorkoverProjectPoolOut]:
    project = patch_project_status(
        db,
        project_id,
        payload.status,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
        comment=payload.comment,
    )
    await push_status_changed(
        {
            "node_code": project.status.value,
            "project_id": project.id,
            "well_no": project.well_no,
        }
    )
    return success(WorkoverProjectPoolOut.model_validate(project), msg="状态已更新")


@router.delete("/{project_id}", response_model=ApiResponse[None])
def delete_item(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workover_project_pool:delete")),
) -> ApiResponse[None]:
    delete_project_pool(
        db,
        project_id,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
    )
    return success(msg="已作废")
