"""Create material_requirement table for Material Management module

Revision ID: 20260705_0008
Revises: 20260705_0007
Create Date: 2026-07-05

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260705_0008"
down_revision: str | None = "20260705_0007"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "material_requirement",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("well_no", sa.String(64), nullable=False, comment="井号"),
        sa.Column("operation_sheet_id", sa.Integer(), sa.ForeignKey("workover_operation_sheet.id", ondelete="SET NULL"), nullable=True, comment="关联修井运行表ID"),
        sa.Column("material_name", sa.String(128), nullable=False, comment="物料名称"),
        sa.Column("specification", sa.String(255), nullable=True, comment="规格型号"),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="1", comment="数量"),
        sa.Column("unit", sa.String(32), nullable=False, server_default="件", comment="计量单位"),
        sa.Column("requirement_type", sa.String(32), nullable=False, server_default="NORMAL", comment="需求类型（正常/紧急）"),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING", comment="物料状态"),
        sa.Column("planned_at", sa.DateTime(timezone=True), nullable=True, comment="计划配送时间"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True, comment="出库时间"),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True, comment="到场确认时间"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True, comment="使用完毕时间"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.Column("extra_info", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"), comment="扩展信息JSONB"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        comment="物料需求与配送表",
    )
    op.create_index("ix_material_requirement_well_no", "material_requirement", ["well_no"])
    op.create_index("ix_material_requirement_status", "material_requirement", ["status"])
    op.create_index("ix_material_requirement_operation_sheet_id", "material_requirement", ["operation_sheet_id"])


def downgrade() -> None:
    op.drop_index("ix_material_requirement_operation_sheet_id", table_name="material_requirement")
    op.drop_index("ix_material_requirement_status", table_name="material_requirement")
    op.drop_index("ix_material_requirement_well_no", table_name="material_requirement")
    op.drop_table("material_requirement")
