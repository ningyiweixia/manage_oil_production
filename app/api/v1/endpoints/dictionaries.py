from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.crud.dictionary import (
    create_dictionary_item,
    delete_dictionary_item,
    list_dictionary_items,
    set_dictionary_item_active,
    update_dictionary_item,
)
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.dictionary import DataDictionaryCreate, DataDictionaryOut, DataDictionaryUpdate
from app.schemas.response import ApiResponse, success

router = APIRouter(prefix="/dictionaries", tags=["data dictionaries"])


@router.get("/", response_model=ApiResponse[list[DataDictionaryOut]])
def list_items(
    dict_type: str | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:dictionary:read")),
) -> ApiResponse[list[DataDictionaryOut]]:
    return success([DataDictionaryOut.model_validate(item) for item in list_dictionary_items(db, dict_type, active_only)])


@router.post("/", response_model=ApiResponse[DataDictionaryOut])
def create_item(
    payload: DataDictionaryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:dictionary:manage")),
) -> ApiResponse[DataDictionaryOut]:
    return success(DataDictionaryOut.model_validate(create_dictionary_item(db, payload)), msg="created")


@router.put("/{item_id}", response_model=ApiResponse[DataDictionaryOut])
def update_item(
    item_id: int,
    payload: DataDictionaryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:dictionary:manage")),
) -> ApiResponse[DataDictionaryOut]:
    return success(DataDictionaryOut.model_validate(update_dictionary_item(db, item_id, payload)), msg="updated")


@router.patch("/{item_id}/active", response_model=ApiResponse[DataDictionaryOut])
def set_active(
    item_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:dictionary:manage")),
) -> ApiResponse[DataDictionaryOut]:
    return success(DataDictionaryOut.model_validate(set_dictionary_item_active(db, item_id, is_active)), msg="updated")


@router.delete("/{item_id}", response_model=ApiResponse[None])
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:dictionary:manage")),
) -> ApiResponse[None]:
    delete_dictionary_item(db, item_id)
    return success(msg="deleted")
