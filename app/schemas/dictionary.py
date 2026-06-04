from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DataDictionaryCreate(BaseModel):
    dict_type: str = Field(min_length=1, max_length=64)
    item_label: str = Field(min_length=1, max_length=128)
    item_value: str = Field(min_length=1, max_length=128)
    is_active: bool = True


class DataDictionaryUpdate(DataDictionaryCreate):
    pass


class DataDictionaryOut(BaseModel):
    id: int
    dict_type: str
    item_label: str
    item_value: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
