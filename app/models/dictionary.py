from sqlalchemy import Boolean, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DataDictionary(TimestampMixin, Base):
    __tablename__ = "data_dictionary"
    __table_args__ = (
        UniqueConstraint("dict_type", "item_value", name="uq_data_dictionary_type_value"),
        Index("ix_data_dictionary_type", "dict_type"),
        {"comment": "Dynamic data dictionary table"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="Dictionary item ID")
    dict_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="Dictionary type")
    item_label: Mapped[str] = mapped_column(String(128), nullable=False, comment="Display label")
    item_value: Mapped[str] = mapped_column(String(128), nullable=False, comment="Business value")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="Whether enabled")
