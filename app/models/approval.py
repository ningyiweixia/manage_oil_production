import enum
from typing import Any

from sqlalchemy import Enum as SQLEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ApprovalAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VOID = "VOID"
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ROLLBACK = "ROLLBACK"


class ApprovalLog(TimestampMixin, Base):
    __tablename__ = "approval_log"
    __table_args__ = (
        Index("ix_approval_log_business", "business_type", "business_id"),
        Index("ix_approval_log_operator_id", "operator_id"),
        {"comment": "审批日志表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="审批日志ID")
    business_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="业务类型")
    business_id: Mapped[int] = mapped_column(nullable=False, comment="业务主键ID")
    node_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="审批节点编码")
    action: Mapped[ApprovalAction] = mapped_column(
        SQLEnum(ApprovalAction, native_enum=False, length=32),
        nullable=False,
        comment="审批动作",
    )
    comment: Mapped[str | None] = mapped_column(Text, comment="审批意见")
    operator_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id"), nullable=False, comment="操作人ID")
    operator_ip: Mapped[str | None] = mapped_column(String(64), comment="操作人IP")
    before_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, comment="变更前数据快照")
    after_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, comment="变更后数据快照")

    operator: Mapped["User"] = relationship(back_populates="approval_logs")
