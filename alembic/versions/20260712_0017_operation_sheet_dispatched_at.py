"""Add independent operation dispatch timestamp.

Revision ID: 20260712_0017
Revises: 20260712_0016
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260712_0017"
down_revision: str | None = "20260712_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("workover_operation_sheet", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True, comment="派工时间"))
    # Existing records predate this field; updated_at is the least-surprising
    # historical approximation without confusing it with A5 synchronization time.
    op.execute(
        "UPDATE workover_operation_sheet SET dispatched_at = updated_at "
        "WHERE dispatched_at IS NULL AND status IN ('DISPATCHED', 'WORKING', 'FINISHED')"
    )


def downgrade() -> None:
    op.drop_column("workover_operation_sheet", "dispatched_at")
