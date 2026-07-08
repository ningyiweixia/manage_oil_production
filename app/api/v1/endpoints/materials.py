"""物料管理与配送 API。

包含物料需求的创建、查询、状态流转和基础统计功能。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
from app.schemas.material import (
    MaterialRequirementCreate,
    MaterialRequirementOut,
    MaterialRequirementQuery,
    MaterialRequirementUpdate,
)
from app.schemas.pagination import PageResult
from app.schemas.response import ApiResponse, success

router = APIRouter(prefix="/materials", tags=["物料管理与配送"])


@router.get("/", response_model=ApiResponse[PageResult[MaterialRequirementOut]])
def list_items(
    query: MaterialRequirementQuery = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("material:read")),
) -> ApiResponse[PageResult[MaterialRequirementOut]]:
    rows, total = list_material_requirements(db, query)
    items = [MaterialRequirementOut.model_validate(row) for row in rows]
    return success(
        PageResult(items=items, total=total, page=query.page, page_size=query.page_size)
    )


@router.post("/", response_model=ApiResponse[MaterialRequirementOut])
def create_item(
    payload: MaterialRequirementCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("material:create")),
) -> ApiResponse[MaterialRequirementOut]:
    obj = create_material_requirement(db, payload)
    return success(MaterialRequirementOut.model_validate(obj), msg="物料需求创建成功")


@router.get("/analytics/summary", response_model=ApiResponse[dict])
def analytics(
    well_no: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("material:read")),
) -> ApiResponse[dict]:
    return success(get_material_analytics(db, well_no))


@router.get("/{req_id}", response_model=ApiResponse[MaterialRequirementOut])
def detail(
    req_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("material:read")),
) -> ApiResponse[MaterialRequirementOut]:
    return success(MaterialRequirementOut.model_validate(get_material_requirement(db, req_id)))


@router.put("/{req_id}", response_model=ApiResponse[MaterialRequirementOut])
def update_item(
    req_id: int,
    payload: MaterialRequirementUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("material:update")),
) -> ApiResponse[MaterialRequirementOut]:
    obj = update_material_requirement(db, req_id, payload)
    return success(MaterialRequirementOut.model_validate(obj), msg="物料需求已更新")


@router.delete("/{req_id}", response_model=ApiResponse[None])
def delete_item(
    req_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("material:delete")),
) -> ApiResponse[None]:
    delete_material_requirement(db, req_id)
    return success(msg="物料需求已删除")


