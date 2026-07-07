"""Add project pool verification fields

Revision ID: 20260707_0011
Revises: 20260705_0010
Create Date: 2026-07-07
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260707_0011"
down_revision: str | None = "20260705_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workover_project_pool",
        sa.Column("geology_verified_daily_oil", sa.Numeric(12, 2), nullable=True, comment="地质/生产核实日产油"),
    )
    op.add_column(
        "workover_project_pool",
        sa.Column("geology_verified_at", sa.DateTime(timezone=True), nullable=True, comment="地质/生产核实时间"),
    )
    op.add_column(
        "workover_project_pool",
        sa.Column("process_well_condition", sa.Text(), nullable=True, comment="工艺核实井况"),
    )
    op.add_column(
        "workover_project_pool",
        sa.Column("process_can_workover", sa.Boolean(), nullable=True, comment="工艺确认是否可以上修"),
    )
    op.add_column(
        "workover_project_pool",
        sa.Column("process_verified_at", sa.DateTime(timezone=True), nullable=True, comment="工艺核实时间"),
    )


def downgrade() -> None:
    op.drop_column("workover_project_pool", "process_verified_at")
    op.drop_column("workover_project_pool", "process_can_workover")
    op.drop_column("workover_project_pool", "process_well_condition")
    op.drop_column("workover_project_pool", "geology_verified_at")
    op.drop_column("workover_project_pool", "geology_verified_daily_oil")
