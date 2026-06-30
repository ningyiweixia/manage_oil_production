"""remove_voided_status

Revision ID: 150795c9dad6
Revises: 20260629_0005
Create Date: 2026-06-30 09:47:47.763885
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '150795c9dad6'
down_revision: Union[str, None] = '20260629_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing VOIDED records are all logically deleted (is_deleted=True).
    # Set their status to DRAFT since VOIDED is no longer a valid value.
    op.execute(
        "UPDATE workover_project_pool SET status = 'DRAFT' WHERE status = 'VOIDED'"
    )


def downgrade() -> None:
    # No need to revert — old VOIDED records were already deleted.
    pass
