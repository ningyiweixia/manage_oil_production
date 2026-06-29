import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ProjectPoolStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_GEOLOGY_VERIFY = "PENDING_GEOLOGY_VERIFY"
    PENDING_PROCESS_VERIFY = "PENDING_PROCESS_VERIFY"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISPATCHED = "DISPATCHED"
    VOIDED = "VOIDED"


class OperationStatus(str, enum.Enum):
    WAITING_DISPATCH = "WAITING_DISPATCH"
    DISPATCHED = "DISPATCHED"
    WORKING = "WORKING"
    FINISHED = "FINISHED"
    CANCELED = "CANCELED"


class ContractorCapacityStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class WorkoverProjectPool(TimestampMixin, Base):
    __tablename__ = "workover_project_pool"
    __table_args__ = (
        Index("ix_workover_project_pool_well_no", "well_no"),
        Index("ix_workover_project_pool_status", "status"),
        Index("ix_workover_project_pool_block_name", "block_name"),
        Index("ix_workover_project_pool_measures_gin", "measures_jsonb", postgresql_using="gin"),
        {"comment": "上修项目池表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="项目池ID")
    well_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="井号")
    well_name: Mapped[str | None] = mapped_column(String(128), comment="Well name")
    layer: Mapped[str | None] = mapped_column(String(128), comment="Layer")
    fault_description: Mapped[str | None] = mapped_column(Text, comment="Fault description")
    territory_unit: Mapped[str | None] = mapped_column(String(128), comment="Territory unit")
    block_name: Mapped[str | None] = mapped_column(String(128), comment="区块")
    report_unit: Mapped[str] = mapped_column(String(128), nullable=False, comment="提报单位")
    production_priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="产量优先级")
    status: Mapped[ProjectPoolStatus] = mapped_column(
        SQLEnum(ProjectPoolStatus, native_enum=False, length=64),
        default=ProjectPoolStatus.DRAFT,
        nullable=False,
        comment="项目状态",
    )
    reason: Mapped[str | None] = mapped_column(Text, comment="上修原因")
    measures_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="修井措施JSONB",
    )
    remark: Mapped[str | None] = mapped_column(Text, comment="Remark")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="审批通过时间")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id", ondelete="SET NULL"), comment="创建人ID")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="Logical delete flag")

    operations: Mapped[list["WorkoverOperationSheet"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ContractorCapacity(TimestampMixin, Base):
    __tablename__ = "contractor_capacity"
    __table_args__ = (
        Index("ix_contractor_capacity_report_date", "report_date"),
        {"comment": "承包商运力表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="运力ID")
    contractor_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="承包商名称")
    team_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="队伍名称")
    report_date: Mapped[date] = mapped_column(Date, nullable=False, comment="日报日期")
    available_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="可用队伍数")
    status: Mapped[ContractorCapacityStatus] = mapped_column(
        SQLEnum(ContractorCapacityStatus, native_enum=False, length=32),
        default=ContractorCapacityStatus.AVAILABLE,
        nullable=False,
        comment="队伍状态",
    )
    capability_tags: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="特定施工能力标签JSONB",
    )

    operations: Mapped[list["WorkoverOperationSheet"]] = relationship(back_populates="contractor_capacity")


class WorkoverOperationSheet(TimestampMixin, Base):
    __tablename__ = "workover_operation_sheet"
    __table_args__ = (
        Index("ix_workover_operation_sheet_status", "status"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_workover_operation_sheet_progress_range"),
        {"comment": "修井运行表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="运行表ID")
    project_id: Mapped[int] = mapped_column(
        ForeignKey("workover_project_pool.id", ondelete="RESTRICT"),
        nullable=False,
        comment="项目池ID",
    )
    contractor_capacity_id: Mapped[int | None] = mapped_column(
        ForeignKey("contractor_capacity.id", ondelete="SET NULL"),
        comment="承包商运力ID",
    )
    operation_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="作业编号")
    status: Mapped[OperationStatus] = mapped_column(
        SQLEnum(OperationStatus, native_enum=False, length=64),
        default=OperationStatus.WAITING_DISPATCH,
        nullable=False,
        comment="作业状态",
    )
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="计划开始时间")
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="计划结束时间")
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="实际开始时间")
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="实际结束时间")
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="施工进度百分比")
    progress_detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="施工进度明细JSONB",
    )

    project: Mapped[WorkoverProjectPool] = relationship(back_populates="operations")
    contractor_capacity: Mapped[ContractorCapacity | None] = relationship(back_populates="operations")
