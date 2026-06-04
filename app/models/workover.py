import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text
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
        {"comment": "Workover project pool table"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="Project pool ID")
    well_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="Well number")
    well_name: Mapped[str | None] = mapped_column(String(128), comment="Well name")
    layer: Mapped[str | None] = mapped_column(String(128), comment="Layer")
    fault_description: Mapped[str | None] = mapped_column(Text, comment="Fault description")
    territory_unit: Mapped[str | None] = mapped_column(String(128), comment="Territory unit")
    block_name: Mapped[str | None] = mapped_column(String(128), comment="Block")
    report_unit: Mapped[str] = mapped_column(String(128), nullable=False, comment="Grass-roots reporting unit")
    production_priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Production priority")
    status: Mapped[ProjectPoolStatus] = mapped_column(
        SQLEnum(ProjectPoolStatus, native_enum=False, length=64),
        default=ProjectPoolStatus.DRAFT,
        nullable=False,
        comment="Business status",
    )
    reason: Mapped[str | None] = mapped_column(Text, comment="Workover reason")
    measures_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="JSONB measures payload; indexed by GIN for PostgreSQL JSON search",
    )
    remark: Mapped[str | None] = mapped_column(Text, comment="Remark")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="Approved time")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id"), comment="Creator ID")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="Logical delete flag")

    operations: Mapped[list["WorkoverOperationSheet"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ContractorCapacity(TimestampMixin, Base):
    __tablename__ = "contractor_capacity"
    __table_args__ = (
        Index("ix_contractor_capacity_report_date", "report_date"),
        {"comment": "Contractor capacity table"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="Capacity ID")
    contractor_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="Contractor name")
    team_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="Team name")
    report_date: Mapped[date] = mapped_column(Date, nullable=False, comment="Report date")
    available_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Available team count")
    status: Mapped[ContractorCapacityStatus] = mapped_column(
        SQLEnum(ContractorCapacityStatus, native_enum=False, length=32),
        default=ContractorCapacityStatus.AVAILABLE,
        nullable=False,
        comment="Capacity status",
    )
    capability_tags: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="JSONB capability tags",
    )

    operations: Mapped[list["WorkoverOperationSheet"]] = relationship(back_populates="contractor_capacity")


class WorkoverOperationSheet(TimestampMixin, Base):
    __tablename__ = "workover_operation_sheet"
    __table_args__ = (
        Index("ix_workover_operation_sheet_status", "status"),
        {"comment": "Workover operation sheet"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="Operation sheet ID")
    project_id: Mapped[int] = mapped_column(
        ForeignKey("workover_project_pool.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Project pool ID",
    )
    contractor_capacity_id: Mapped[int | None] = mapped_column(
        ForeignKey("contractor_capacity.id", ondelete="SET NULL"),
        comment="Contractor capacity ID",
    )
    operation_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="Operation number")
    status: Mapped[OperationStatus] = mapped_column(
        SQLEnum(OperationStatus, native_enum=False, length=64),
        default=OperationStatus.WAITING_DISPATCH,
        nullable=False,
        comment="Operation status",
    )
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="Planned start time")
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="Planned end time")
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="Actual start time")
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="Actual end time")
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Progress percentage")
    progress_detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="JSONB progress detail",
    )

    project: Mapped[WorkoverProjectPool] = relationship(back_populates="operations")
    contractor_capacity: Mapped[ContractorCapacity | None] = relationship(back_populates="operations")
