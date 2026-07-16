"""完井分类台账 API。

包含完井记录的创建、查询、统计功能。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.crud.completion import (
    create_completion_record,
    delete_completion_record,
    get_completion_analytics,
    get_completion_record,
    list_completion_records,
    update_completion_record,
)
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.completion import (
    WellCompletionCreate,
    WellCompletionOut,
    WellCompletionQuery,
    WellCompletionUpdate,
)
from app.schemas.pagination import PageResult
from app.schemas.response import ApiResponse, success

router = APIRouter(prefix="/well-completions", tags=["完井分类台账"])


@router.get("/", response_model=ApiResponse[PageResult[WellCompletionOut]])
def list_items(
    query: WellCompletionQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("completion:read")),
) -> ApiResponse[PageResult[WellCompletionOut]]:
    rows, total = list_completion_records(db, query, current_user=current_user)
    items = [WellCompletionOut.model_validate(row) for row in rows]
    return success(
        PageResult(items=items, total=total, page=query.page, page_size=query.page_size)
    )


@router.post("/", response_model=ApiResponse[WellCompletionOut])
def create_item(
    payload: WellCompletionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("completion:create")),
) -> ApiResponse[WellCompletionOut]:
    obj = create_completion_record(db, payload, current_user=current_user)
    return success(WellCompletionOut.model_validate(obj), msg="完井记录创建成功")


@router.get("/analytics/summary", response_model=ApiResponse[dict])
def analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("completion:read")),
) -> ApiResponse[dict]:
    return success(get_completion_analytics(db, current_user=current_user))


@router.get("/{record_id}", response_model=ApiResponse[WellCompletionOut])
def detail(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("completion:read")),
) -> ApiResponse[WellCompletionOut]:
    return success(WellCompletionOut.model_validate(get_completion_record(db, record_id, current_user=current_user)))


@router.put("/{record_id}", response_model=ApiResponse[WellCompletionOut])
def update_item(
    record_id: int,
    payload: WellCompletionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("completion:update")),
) -> ApiResponse[WellCompletionOut]:
    obj = update_completion_record(db, record_id, payload, current_user=current_user)
    return success(WellCompletionOut.model_validate(obj), msg="完井记录已更新")


@router.delete("/{record_id}", response_model=ApiResponse[None])
def delete_item(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("completion:delete")),
) -> ApiResponse[None]:
    delete_completion_record(db, record_id, current_user=current_user)
    return success(msg="完井记录已删除")
