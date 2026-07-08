"""Add closed-loop fields to material requirements

Revision ID: 20260708_0002
Revises: 20260708_0001
Create Date: 2026-07-08

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260708_0002"
down_revision: str | None = "20260708_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("material_requirement", sa.Column("plan_no", sa.String(64), nullable=True, comment="物料计划号"))
    op.add_column("material_requirement", sa.Column("warehouse", sa.String(128), nullable=True, comment="仓库"))
    op.add_column("material_requirement", sa.Column("supplier_or_team", sa.String(128), nullable=True, comment="供应商或配送队伍"))
    op.add_column("material_requirement", sa.Column("planned_quantity", sa.Float(), nullable=False, server_default="0", comment="计划数量"))
    op.add_column("material_requirement", sa.Column("delivered_quantity", sa.Float(), nullable=False, server_default="0", comment="出库数量"))
    op.add_column("material_requirement", sa.Column("arrived_quantity", sa.Float(), nullable=False, server_default="0", comment="到场数量"))
    op.add_column("material_requirement", sa.Column("used_quantity", sa.Float(), nullable=False, server_default="0", comment="使用数量"))
    op.add_column("material_requirement", sa.Column("delivery_contact", sa.String(64), nullable=True, comment="配送联系人"))
    op.add_column("material_requirement", sa.Column("delivery_phone", sa.String(32), nullable=True, comment="配送联系电话"))
    op.add_column("material_requirement", sa.Column("expected_arrival_at", sa.DateTime(timezone=True), nullable=True, comment="预计到场时间"))
    op.add_column("material_requirement", sa.Column("exception_reason", sa.Text(), nullable=True, comment="异常情况"))
    op.add_column("material_requirement", sa.Column("source_platform", sa.String(32), nullable=False, server_default="internal", comment="来源平台"))
    op.add_column("material_requirement", sa.Column("external_material_id", sa.String(128), nullable=True, comment="外部物料记录ID"))


def downgrade() -> None:
    op.drop_column("material_requirement", "external_material_id")
    op.drop_column("material_requirement", "source_platform")
    op.drop_column("material_requirement", "exception_reason")
    op.drop_column("material_requirement", "expected_arrival_at")
    op.drop_column("material_requirement", "delivery_phone")
    op.drop_column("material_requirement", "delivery_contact")
    op.drop_column("material_requirement", "used_quantity")
    op.drop_column("material_requirement", "arrived_quantity")
    op.drop_column("material_requirement", "delivered_quantity")
    op.drop_column("material_requirement", "planned_quantity")
    op.drop_column("material_requirement", "supplier_or_team")
    op.drop_column("material_requirement", "warehouse")
    op.drop_column("material_requirement", "plan_no")
