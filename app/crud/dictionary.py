from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.models.dictionary import DataDictionary
from app.schemas.dictionary import DataDictionaryCreate, DataDictionaryUpdate


def list_dictionary_items(
    db: Session,
    dict_type: str | None = None,
    active_only: bool = True,
) -> list[DataDictionary]:
    stmt = select(DataDictionary)
    if dict_type:
        stmt = stmt.where(DataDictionary.dict_type == dict_type)
    if active_only:
        stmt = stmt.where(DataDictionary.is_active.is_(True))
    stmt = stmt.order_by(DataDictionary.dict_type.asc(), DataDictionary.id.asc())
    return list(db.scalars(stmt).all())


def get_dictionary_item(db: Session, item_id: int) -> DataDictionary:
    item = db.get(DataDictionary, item_id)
    if item is None:
        raise BusinessException(BAD_REQUEST, "dictionary item not found")
    return item


def create_dictionary_item(db: Session, payload: DataDictionaryCreate) -> DataDictionary:
    exists = db.scalar(
        select(DataDictionary).where(
            DataDictionary.dict_type == payload.dict_type,
            DataDictionary.item_value == payload.item_value,
        )
    )
    if exists is not None:
        raise BusinessException(CONFLICT, "dictionary item already exists")
    item = DataDictionary(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_dictionary_item(db: Session, item_id: int, payload: DataDictionaryUpdate) -> DataDictionary:
    item = get_dictionary_item(db, item_id)
    duplicate = db.scalar(
        select(DataDictionary).where(
            DataDictionary.id != item_id,
            DataDictionary.dict_type == payload.dict_type,
            DataDictionary.item_value == payload.item_value,
        )
    )
    if duplicate is not None:
        raise BusinessException(CONFLICT, "dictionary item already exists")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def set_dictionary_item_active(db: Session, item_id: int, is_active: bool) -> DataDictionary:
    item = get_dictionary_item(db, item_id)
    item.is_active = is_active
    db.commit()
    db.refresh(item)
    return item
