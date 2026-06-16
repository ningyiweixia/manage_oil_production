from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST
from app.models.dictionary import DataDictionary


def ensure_dictionary_values(db: Session, dict_type: str, values: set[str]) -> None:
    if not values:
        return
    stmt = select(DataDictionary.item_value, DataDictionary.item_label).where(
        DataDictionary.dict_type == dict_type,
        or_(DataDictionary.item_value.in_(values), DataDictionary.item_label.in_(values)),
        DataDictionary.is_active.is_(True),
    )
    existing: set[str] = set()
    for item_value, item_label in db.execute(stmt).all():
        existing.add(item_value)
        existing.add(item_label)
    missing = values - existing
    if missing:
        raise BusinessException(BAD_REQUEST, f"数据字典缺少有效取值: {dict_type}={sorted(missing)}")
