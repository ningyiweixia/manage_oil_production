"""add trace id to operation logs

Revision ID: 20260706_0011
Revises: 20260705_0010
Create Date: 2026-07-06 18:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260706_0011"
down_revision = "20260705_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sys_operation_log", sa.Column("trace_id", sa.String(length=64), nullable=True, comment="Request trace ID"))
    op.create_index("ix_sys_operation_log_trace_id", "sys_operation_log", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sys_operation_log_trace_id", table_name="sys_operation_log")
    op.drop_column("sys_operation_log", "trace_id")
