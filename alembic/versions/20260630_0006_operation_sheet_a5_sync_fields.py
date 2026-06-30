"""add operation sheet a5 sync fields

Revision ID: 20260630_0006
Revises: 150795c9dad6
Create Date: 2026-06-30 11:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260630_0006"
down_revision: Union[str, None] = "150795c9dad6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workover_operation_sheet", sa.Column("a5_status", sa.String(length=64), nullable=True, comment="A5工单状态"))
    op.add_column("workover_operation_sheet", sa.Column("a5_remark", sa.Text(), nullable=True, comment="A5回写备注"))
    op.add_column("workover_operation_sheet", sa.Column("last_a5_sync_at", sa.DateTime(timezone=True), nullable=True, comment="最近A5同步时间"))


def downgrade() -> None:
    op.drop_column("workover_operation_sheet", "last_a5_sync_at")
    op.drop_column("workover_operation_sheet", "a5_remark")
    op.drop_column("workover_operation_sheet", "a5_status")
