import enum
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class MaterialRequirementStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PLANNED = "PLANNED"
    DELIVERED = "DELIVERED"
    ARRIVED = "ARRIVED"
    USED = "USED"
    CANCELED = "CANCELED"


class MaterialRequirementType(str, enum.Enum):
    NORMAL = "NORMAL"
    EMERGENCY = "EMERGENCY"


class MaterialRequirement(TimestampMixin, Base):
    __tablename__ = "material_requirement"
    __table_args__ = (
        Index("ix_material_requirement_well_no", "well_no"),
        Index("ix_material_requirement_status", "status"),
        Index("ix_material_requirement_operation_sheet_id", "operation_sheet_id"),
        {"comment": "物料需求与配送表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="物料需求ID")
    well_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="井号")
    operation_sheet_id: Mapped[int | None] = mapped_column(
        ForeignKey("workover_operation_sheet.id", ondelete="SET NULL"),
        comment="关联修井运行表ID",
    )
    material_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="物料名称")
    specification: Mapped[str | None] = mapped_column(String(255), comment="规格型号")
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1, comment="数量")
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="件", comment="计量单位")
    plan_no: Mapped[str | None] = mapped_column(String(64), comment="物料计划号")
    warehouse: Mapped[str | None] = mapped_column(String(128), comment="仓库")
    supplier_or_team: Mapped[str | None] = mapped_column(String(128), comment="供应商或配送队伍")
    planned_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="计划数量")
    delivered_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="出库数量")
    arrived_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="到场数量")
    used_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="使用数量")
    delivery_contact: Mapped[str | None] = mapped_column(String(64), comment="配送联系人")
    delivery_phone: Mapped[str | None] = mapped_column(String(32), comment="配送联系电话")
    expected_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="预计到场时间")
    exception_reason: Mapped[str | None] = mapped_column(Text, comment="异常情况")
    source_platform: Mapped[str] = mapped_column(String(32), nullable=False, default="internal", comment="来源平台")
    external_material_id: Mapped[str | None] = mapped_column(String(128), comment="外部物料记录ID")
    requirement_type: Mapped[MaterialRequirementType] = mapped_column(
        SQLEnum(MaterialRequirementType, native_enum=False, length=32),
        default=MaterialRequirementType.NORMAL,
        nullable=False,
        comment="需求类型（正常/紧急）",
    )
    status: Mapped[MaterialRequirementStatus] = mapped_column(
        SQLEnum(MaterialRequirementStatus, native_enum=False, length=32),
        default=MaterialRequirementStatus.PENDING,
        nullable=False,
        comment="物料状态",
    )
    planned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="计划配送时间")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="出库时间")
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="到场确认时间")
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="使用完毕时间")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    extra_info: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, comment="扩展信息JSONB"
    )
