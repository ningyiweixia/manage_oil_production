"""Merge two parallel migration branches

Revision ID: 20260708_0001
Revises: 20260707_0012, 20260707_0013
Create Date: 2026-07-08

"""
from typing import Sequence

from alembic import op

revision: str = "20260708_0001"
down_revision: tuple[str, str] | None = ("20260707_0012", "20260707_0013")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
