"""Add well_type, county, initiator fields, photo_urls to workover_project_pool

Revision ID: 20260705_0007
Revises: 20260630_0006
Create Date: 2026-07-05

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260705_0007"
down_revision: str | None = "20260630_0006"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("workover_project_pool", sa.Column("well_type", sa.String(64), nullable=True, comment="井别（油井/水井/注气井等）"))
    op.add_column("workover_project_pool", sa.Column("county", sa.String(64), nullable=True, comment="县区"))
    op.add_column("workover_project_pool", sa.Column("initiator_name", sa.String(64), nullable=True, comment="发起人"))
    op.add_column("workover_project_pool", sa.Column("initiator_phone", sa.String(32), nullable=True, comment="发起人联系电话"))
    op.add_column("workover_project_pool", sa.Column("photo_urls", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"), comment="照片附件URL列表JSONB"))
    op.create_index("ix_workover_project_pool_report_unit", "workover_project_pool", ["report_unit"])


def downgrade() -> None:
    op.drop_index("ix_workover_project_pool_report_unit", table_name="workover_project_pool")
    op.drop_column("workover_project_pool", "photo_urls")
    op.drop_column("workover_project_pool", "initiator_phone")
    op.drop_column("workover_project_pool", "initiator_name")
    op.drop_column("workover_project_pool", "county")
    op.drop_column("workover_project_pool", "well_type")
