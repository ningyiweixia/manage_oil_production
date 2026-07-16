"""物料管理与配送 API。

包含物料需求的创建、查询、状态流转和基础统计功能。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import FORBIDDEN
from app.api.deps import require_permission
from app.crud.material import (
    create_material_requirement,
    delete_material_requirement,
    get_material_analytics,
    get_material_requirement,
    list_material_requirements,
    update_material_requirement,
)
from app.db.session import get_db
from app.models.rbac import User
from app.services.material_external_adapter import (
    apply_external_material_event,
    get_material_external_adapter,
)
from app.services.data_scope_service import build_data_scope
from app.schemas.material import (
    MaterialRequirementCreate,
    MaterialRequirementOut,
    MaterialRequirementQuery,
    MaterialRequirementUpdate,
)
from app.schemas.pagination import PageResult
from app.schemas.response import ApiResponse, success

router = APIRouter(prefix="/materials", tags=["物料管理与配送"])


def ensure_material_update_allowed(user: User, target_status: object | None) -> None:
    if target_status is None or user.is_superuser:
        return
    role_codes = {role.code for role in user.roles}
    if role_codes & {"super_admin", "ops_admin", "project_pool_admin", "business_reviewer"}:
        return
    if "contractor_operator" in role_codes:
        status_value = getattr(target_status, "value", target_status)
        if status_value in {"ARRIVED", "USED"}:
            return
        raise BusinessException(FORBIDDEN, "承包商只能确认物料到场或使用")
    raise BusinessException(FORBIDDEN, "无权推进物料状态")


@router.get("/", response_model=ApiResponse[PageResult[MaterialRequirementOut]])
def list_items(
    query: MaterialRequirementQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material:read")),
) -> ApiResponse[PageResult[MaterialRequirementOut]]:
    rows, total = list_material_requirements(db, query, scope=build_data_scope(current_user))
    items = [MaterialRequirementOut.model_validate(row) for row in rows]
    return success(
        PageResult(items=items, total=total, page=query.page, page_size=query.page_size)
    )


@router.post("/", response_model=ApiResponse[MaterialRequirementOut])
def create_item(
    payload: MaterialRequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material:create")),
) -> ApiResponse[MaterialRequirementOut]:
    obj = create_material_requirement(db, payload, scope=build_data_scope(current_user))
    return success(MaterialRequirementOut.model_validate(obj), msg="物料需求创建成功")


@router.get("/analytics/summary", response_model=ApiResponse[dict])
def analytics(
    well_no: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material:read")),
) -> ApiResponse[dict]:
    return success(get_material_analytics(db, well_no, scope=build_data_scope(current_user)))


@router.post("/external/sync", response_model=ApiResponse[dict])
async def sync_external_material_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material:update")),
) -> ApiResponse[dict]:
    """Fetch and apply material events from the configured adapter."""
    adapter = get_material_external_adapter()
    results = [
        apply_external_material_event(db, event, scope=build_data_scope(current_user))
        for event in await adapter.fetch_events()
    ]
    duplicates = sum(result.duplicate for result in results)
    return success({
        "total": len(results),
        "processed": len(results) - duplicates,
        "duplicates": duplicates,
    }, msg="物料外部事件同步完成")


@router.get("/{req_id}", response_model=ApiResponse[MaterialRequirementOut])
def detail(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material:read")),
) -> ApiResponse[MaterialRequirementOut]:
    return success(MaterialRequirementOut.model_validate(get_material_requirement(db, req_id, scope=build_data_scope(current_user))))


@router.put("/{req_id}", response_model=ApiResponse[MaterialRequirementOut])
def update_item(
    req_id: int,
    payload: MaterialRequirementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material:update")),
) -> ApiResponse[MaterialRequirementOut]:
    ensure_material_update_allowed(current_user, payload.status)
    obj = update_material_requirement(db, req_id, payload, scope=build_data_scope(current_user))
    return success(MaterialRequirementOut.model_validate(obj), msg="物料需求已更新")


@router.delete("/{req_id}", response_model=ApiResponse[None])
def delete_item(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material:delete")),
) -> ApiResponse[None]:
    delete_material_requirement(db, req_id, scope=build_data_scope(current_user))
    return success(msg="物料需求已删除")


