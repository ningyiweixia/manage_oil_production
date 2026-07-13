import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
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
    EXCEPTION = "EXCEPTION"


class ContractorCapacitySourceType(str, enum.Enum):
    EXTERNAL_SYNC = "EXTERNAL_SYNC"
    LOCAL_SUPPLEMENT = "LOCAL_SUPPLEMENT"
    SYNC_ERROR = "SYNC_ERROR"


class ContractorCapacitySyncStatus(str, enum.Enum):
    SYNCED = "SYNCED"
    PENDING_CONFIRM = "PENDING_CONFIRM"
    CONFLICT = "CONFLICT"
    INVALID = "INVALID"


class ContractorCapacitySyncType(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"
    SINGLE_TEAM = "SINGLE_TEAM"


class ContractorCapacitySyncResultStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class WorkoverProjectPool(TimestampMixin, Base):
    __tablename__ = "workover_project_pool"
    __table_args__ = (
        Index("ix_workover_project_pool_well_no", "well_no"),
        Index("ix_workover_project_pool_status", "status"),
        Index("ix_workover_project_pool_block_name", "block_name"),
        Index("ix_workover_project_pool_measures_gin", "measures_jsonb", postgresql_using="gin"),
        Index("ix_workover_project_pool_report_unit", "report_unit"),
        {"comment": "上修项目池表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="项目池ID")
    well_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="井号")
    well_name: Mapped[str | None] = mapped_column(String(128), comment="井名")
    well_type: Mapped[str | None] = mapped_column(String(64), comment="井别（油井/水井/注气井等）")
    layer: Mapped[str | None] = mapped_column(String(128), comment="层位")
    fault_description: Mapped[str | None] = mapped_column(Text, comment="故障描述")
    territory_unit: Mapped[str | None] = mapped_column(String(128), comment="作业区")
    block_name: Mapped[str | None] = mapped_column(String(128), comment="区块")
    county: Mapped[str | None] = mapped_column(String(64), comment="县区")
    report_unit: Mapped[str] = mapped_column(String(128), nullable=False, comment="提报单位")
    initiator_name: Mapped[str | None] = mapped_column(String(64), comment="发起人")
    initiator_phone: Mapped[str | None] = mapped_column(String(32), comment="发起人联系电话")
    production_priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="产量优先级")
    geology_verified_daily_oil: Mapped[float | None] = mapped_column(Numeric(12, 2), comment="地质/生产核实日产油")
    geology_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="地质/生产核实时间")
    process_well_condition: Mapped[str | None] = mapped_column(Text, comment="工艺核实井况")
    process_can_workover: Mapped[bool | None] = mapped_column(Boolean, comment="工艺确认是否可以上修")
    process_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="工艺核实时间")
    status: Mapped[ProjectPoolStatus] = mapped_column(
        SQLEnum(ProjectPoolStatus, native_enum=False, length=64),
        default=ProjectPoolStatus.DRAFT,
        nullable=False,
        comment="项目状态",
    )
    reason: Mapped[str | None] = mapped_column(Text, comment="上修原因")
    reason_category: Mapped[str | None] = mapped_column(String(64), comment="提报原因分类")
    completeness_status: Mapped[str] = mapped_column(String(32), default="INCOMPLETE", nullable=False, comment="资料完整性状态")
    data_source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False, comment="数据来源")
    report_batch: Mapped[str | None] = mapped_column(String(64), comment="提报批次")
    photo_requirement: Mapped[str | None] = mapped_column(String(255), comment="照片资料要求")
    rejection_supplement: Mapped[str | None] = mapped_column(Text, comment="退回补充材料说明")
    is_duplicate_well: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否重复井号提报")
    related_project_ids: Mapped[list[int]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="关联历史项目ID列表",
    )
    measures_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="修井措施JSONB",
    )
    photo_urls: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="照片附件URL列表JSONB",
    )
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="附件元数据列表JSONB",
    )
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="审批通过时间")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id", ondelete="SET NULL"), comment="创建人ID")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="逻辑删除标记")

    operations: Mapped[list["WorkoverOperationSheet"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ContractorCapacity(TimestampMixin, Base):
    __tablename__ = "contractor_capacity"
    __table_args__ = (
        Index("ix_contractor_capacity_report_date", "report_date"),
        Index("ix_contractor_capacity_external_system_id", "external_system_id"),
        Index("ix_contractor_capacity_source_type", "source_type"),
        Index("ix_contractor_capacity_sync_status", "sync_status"),
        Index("ix_contractor_capacity_created_by_id", "created_by_id"),
        UniqueConstraint("contractor_name", "team_name", "report_date", name="uq_contractor_capacity_team_daily"),
        UniqueConstraint("external_system_id", "report_date", name="uq_contractor_capacity_external_daily"),
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
    external_system_id: Mapped[str | None] = mapped_column(String(128), comment="外部承包商系统队伍ID")
    external_status: Mapped[str | None] = mapped_column(String(64), comment="外部系统原始状态")
    source_type: Mapped[ContractorCapacitySourceType] = mapped_column(
        SQLEnum(ContractorCapacitySourceType, native_enum=False, length=32),
        default=ContractorCapacitySourceType.LOCAL_SUPPLEMENT,
        nullable=False,
        comment="数据来源",
    )
    sync_status: Mapped[ContractorCapacitySyncStatus] = mapped_column(
        SQLEnum(ContractorCapacitySyncStatus, native_enum=False, length=32),
        default=ContractorCapacitySyncStatus.PENDING_CONFIRM,
        nullable=False,
        comment="同步状态",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="最近同步时间")
    sync_error_message: Mapped[str | None] = mapped_column(Text, comment="同步异常信息")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="人工确认时间")
    confirmed_by_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id", ondelete="SET NULL"), comment="确认人ID")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id", ondelete="SET NULL"), comment="创建人ID")
    contact_name: Mapped[str | None] = mapped_column(String(64), comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(32), comment="联系电话")
    qualification_expire_at: Mapped[date | None] = mapped_column(Date, comment="资质有效期")
    equipment_summary: Mapped[str | None] = mapped_column(Text, comment="设备概况")

    operations: Mapped[list["WorkoverOperationSheet"]] = relationship(back_populates="contractor_capacity")

    @property
    def occupied_count(self) -> int:
        loaded_count = getattr(self, "_occupied_count", None)
        if loaded_count is not None:
            return int(loaded_count)
        active_statuses = {OperationStatus.DISPATCHED, OperationStatus.WORKING}
        return len([item for item in self.operations if item.status in active_statuses])


class ContractorCapacitySyncLog(TimestampMixin, Base):
    __tablename__ = "contractor_capacity_sync_log"
    __table_args__ = (
        Index("ix_contractor_capacity_sync_log_started_at", "started_at"),
        Index("ix_contractor_capacity_sync_log_status", "status"),
        {"comment": "承包商运力同步日志表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="同步日志ID")
    sync_type: Mapped[ContractorCapacitySyncType] = mapped_column(
        SQLEnum(ContractorCapacitySyncType, native_enum=False, length=32),
        nullable=False,
        comment="同步方式",
    )
    status: Mapped[ContractorCapacitySyncResultStatus] = mapped_column(
        SQLEnum(ContractorCapacitySyncResultStatus, native_enum=False, length=32),
        nullable=False,
        comment="同步结果",
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="结束时间")
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="成功数量")
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="失败数量")
    created_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="新增数量")
    updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="更新数量")
    ignored_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="忽略数量")
    error_message: Mapped[str | None] = mapped_column(Text, comment="失败原因")
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id", ondelete="SET NULL"), comment="操作人ID")
    raw_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, comment="原始摘要")


class WorkoverOperationSheet(TimestampMixin, Base):
    __tablename__ = "workover_operation_sheet"
    __table_args__ = (
        Index("ix_workover_operation_sheet_status", "status"),
        UniqueConstraint("project_id", name="uq_workover_operation_sheet_project"),
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
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="派工时间")
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="实际开始时间")
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="实际结束时间")
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="施工进度百分比")
    progress_detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="施工进度明细JSONB",
    )
    a5_status: Mapped[str | None] = mapped_column(String(64), comment="A5工单状态")
    a5_remark: Mapped[str | None] = mapped_column(Text, comment="A5回写备注")
    last_a5_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="最近A5同步时间")

    project: Mapped[WorkoverProjectPool] = relationship(back_populates="operations")
    contractor_capacity: Mapped[ContractorCapacity | None] = relationship(back_populates="operations")

    @property
    def project_well_no(self) -> str | None:
        return self.project.well_no if self.project is not None else None
