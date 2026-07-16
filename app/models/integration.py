import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum as SQLEnum, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class IntegrationEventStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    PENDING_REVIEW = "PENDING_REVIEW"
    FAILED = "FAILED"


class IntegrationEvent(TimestampMixin, Base):
    __tablename__ = "integration_event"
    __table_args__ = (
        UniqueConstraint("source", "event_key", name="uq_integration_event_source_key"),
        Index("ix_integration_event_source_status", "source", "status"),
        Index("ix_integration_event_operation_no", "operation_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    event_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[IntegrationEventStatus] = mapped_column(
        SQLEnum(IntegrationEventStatus, native_enum=False, length=32),
        default=IntegrationEventStatus.RECEIVED,
        nullable=False,
    )
    operation_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
