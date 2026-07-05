"""Create well_completion_record table for Well Completion Ledger

Revision ID: 20260705_0009
Revises: 20260705_0008
Create Date: 2026-07-05

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260705_0009"
down_revision: str | None = "20260705_0008"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "well_completion_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("well_no", sa.String(64), nullable=False, comment="井号"),
        sa.Column("operation_sheet_id", sa.Integer(), sa.ForeignKey("workover_operation_sheet.id", ondelete="SET NULL"), nullable=True, comment="关联修井运行表ID"),
        sa.Column("measure_type", sa.String(64), nullable=False, comment="措施类型"),
        sa.Column("completion_date", sa.Date(), nullable=True, comment="完井日期"),
        sa.Column("team_name", sa.String(128), nullable=True, comment="施工队伍"),
        sa.Column("pre_repair_data", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"), comment="修前关键数据JSONB"),
        sa.Column("post_repair_data", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"), comment="修后关键数据JSONB"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        comment="完井分类台账表",
    )
    op.create_index("ix_well_completion_well_no", "well_completion_record", ["well_no"])
    op.create_index("ix_well_completion_measure_type", "well_completion_record", ["measure_type"])
    op.create_index("ix_well_completion_completion_date", "well_completion_record", ["completion_date"])


def downgrade() -> None:
    op.drop_index("ix_well_completion_completion_date", table_name="well_completion_record")
    op.drop_index("ix_well_completion_measure_type", table_name="well_completion_record")
    op.drop_index("ix_well_completion_well_no", table_name="well_completion_record")
    op.drop_table("well_completion_record")
