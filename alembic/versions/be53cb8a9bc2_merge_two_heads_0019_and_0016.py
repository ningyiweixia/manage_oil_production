"""merge two heads 0019 and 0016

Revision ID: be53cb8a9bc2
Revises: 20260713_0019, 20260716_0016_integration_events
Create Date: 2026-07-16 15:29:47.696792
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'be53cb8a9bc2'
down_revision: Union[str, None] = ('20260713_0019', '20260716_0016_integration_events')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
