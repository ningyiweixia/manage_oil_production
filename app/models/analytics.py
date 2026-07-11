import enum

from datetime import datetime

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class AnalyticsAlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    PROCESSING = "PROCESSING"
    CLOSED = "CLOSED"


class AnalyticsAlert(TimestampMixin, Base):
    __tablename__ = "analytics_alert"
    __table_args__ = (
        Index("ix_analytics_alert_status", "status"),
        Index("ix_analytics_alert_assignee_id", "assignee_id"),
        UniqueConstraint("alert_key", name="uq_analytics_alert_alert_key"),
        {"comment": "统计分析告警表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="告警ID")
    alert_key: Mapped[str] = mapped_column(String(128), nullable=False, comment="告警唯一键")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="告警标题")
    message: Mapped[str] = mapped_column(Text, nullable=False, comment="告警内容")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", comment="告警级别")
    source_module: Mapped[str] = mapped_column(String(64), nullable=False, comment="来源模块")
    business_type: Mapped[str | None] = mapped_column(String(64), comment="关联业务类型")
    business_id: Mapped[int | None] = mapped_column(comment="关联业务ID")
    status: Mapped[AnalyticsAlertStatus] = mapped_column(
        SQLEnum(AnalyticsAlertStatus, native_enum=False, length=32),
        default=AnalyticsAlertStatus.OPEN,
        nullable=False,
        comment="告警状态",
    )
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id", ondelete="SET NULL"), comment="处理人ID")
    assignee_name: Mapped[str | None] = mapped_column(String(64), comment="处理人名称")
    remark: Mapped[str | None] = mapped_column(Text, comment="处理备注")
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="创建时间")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="处理中时间")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="关闭时间")
    processed_by_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id", ondelete="SET NULL"), comment="处理人ID")
    closed_by_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id", ondelete="SET NULL"), comment="关闭人ID")

    assignee = relationship("User", foreign_keys=[assignee_id], passive_deletes=True)
    processed_by = relationship("User", foreign_keys=[processed_by_id], passive_deletes=True)
    closed_by = relationship("User", foreign_keys=[closed_by_id], passive_deletes=True)
