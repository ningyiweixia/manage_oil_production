"""Add business quality fields to project pool

Revision ID: 20260707_0012
Revises: 20260706_0011
Create Date: 2026-07-07

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260707_0012"
down_revision: str | None = "20260706_0011"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("workover_project_pool", sa.Column("reason_category", sa.String(64), nullable=True, comment="提报原因分类"))
    op.add_column("workover_project_pool", sa.Column("completeness_status", sa.String(32), nullable=False, server_default="INCOMPLETE", comment="资料完整性状态"))
    op.add_column("workover_project_pool", sa.Column("data_source", sa.String(32), nullable=False, server_default="manual", comment="数据来源"))
    op.add_column("workover_project_pool", sa.Column("report_batch", sa.String(64), nullable=True, comment="提报批次"))
    op.add_column("workover_project_pool", sa.Column("photo_requirement", sa.String(255), nullable=True, comment="照片资料要求"))
    op.add_column("workover_project_pool", sa.Column("rejection_supplement", sa.Text(), nullable=True, comment="退回补充材料说明"))
    op.add_column("workover_project_pool", sa.Column("is_duplicate_well", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否重复井号提报"))
    op.add_column("workover_project_pool", sa.Column("related_project_ids", JSONB, nullable=False, server_default=sa.text("'[]'"), comment="关联历史项目ID列表"))
    op.add_column("workover_project_pool", sa.Column("attachments", JSONB, nullable=False, server_default=sa.text("'[]'"), comment="附件元数据列表JSONB"))
    op.create_index("ix_workover_project_pool_report_batch", "workover_project_pool", ["report_batch"])


def downgrade() -> None:
    op.drop_index("ix_workover_project_pool_report_batch", table_name="workover_project_pool")
    op.drop_column("workover_project_pool", "attachments")
    op.drop_column("workover_project_pool", "related_project_ids")
    op.drop_column("workover_project_pool", "is_duplicate_well")
    op.drop_column("workover_project_pool", "rejection_supplement")
    op.drop_column("workover_project_pool", "photo_requirement")
    op.drop_column("workover_project_pool", "report_batch")
    op.drop_column("workover_project_pool", "data_source")
    op.drop_column("workover_project_pool", "completeness_status")
    op.drop_column("workover_project_pool", "reason_category")
