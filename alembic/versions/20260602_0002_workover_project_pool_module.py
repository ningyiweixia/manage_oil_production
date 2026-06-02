"""workover project pool module

Revision ID: 20260602_0002
Revises: 20260531_0001
Create Date: 2026-06-02 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260602_0002"
down_revision: Union[str, None] = "20260531_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_dictionary",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="Dictionary item ID"),
        sa.Column("dict_type", sa.String(length=64), nullable=False, comment="Dictionary type"),
        sa.Column("item_label", sa.String(length=128), nullable=False, comment="Display label"),
        sa.Column("item_value", sa.String(length=128), nullable=False, comment="Business value"),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="Whether enabled"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_dictionary")),
        sa.UniqueConstraint("dict_type", "item_value", name="uq_data_dictionary_type_value"),
        comment="Dynamic data dictionary table",
    )
    op.create_index("ix_data_dictionary_type", "data_dictionary", ["dict_type"], unique=False)

    op.drop_index("ix_workover_project_pool_measures_gin", table_name="workover_project_pool")
    op.alter_column(
        "workover_project_pool",
        "workover_measures",
        new_column_name="measures_jsonb",
        existing_type=postgresql.JSONB(),
        existing_nullable=False,
    )
    op.add_column("workover_project_pool", sa.Column("well_name", sa.String(length=128), nullable=True, comment="Well name"))
    op.add_column("workover_project_pool", sa.Column("layer", sa.String(length=128), nullable=True, comment="Layer"))
    op.add_column("workover_project_pool", sa.Column("fault_description", sa.Text(), nullable=True, comment="Fault description"))
    op.add_column("workover_project_pool", sa.Column("territory_unit", sa.String(length=128), nullable=True, comment="Territory unit"))
    op.add_column("workover_project_pool", sa.Column("remark", sa.Text(), nullable=True, comment="Remark"))
    op.add_column(
        "workover_project_pool",
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False, comment="Logical delete flag"),
    )
    op.create_index("ix_workover_project_pool_measures_gin", "workover_project_pool", ["measures_jsonb"], unique=False, postgresql_using="gin")
    op.create_index("ix_workover_project_pool_status", "workover_project_pool", ["status"], unique=False)
    op.create_index("ix_workover_project_pool_block_name", "workover_project_pool", ["block_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workover_project_pool_block_name", table_name="workover_project_pool")
    op.drop_index("ix_workover_project_pool_status", table_name="workover_project_pool")
    op.drop_index("ix_workover_project_pool_measures_gin", table_name="workover_project_pool")
    op.drop_column("workover_project_pool", "is_deleted")
    op.drop_column("workover_project_pool", "remark")
    op.drop_column("workover_project_pool", "territory_unit")
    op.drop_column("workover_project_pool", "fault_description")
    op.drop_column("workover_project_pool", "layer")
    op.drop_column("workover_project_pool", "well_name")
    op.alter_column(
        "workover_project_pool",
        "measures_jsonb",
        new_column_name="workover_measures",
        existing_type=postgresql.JSONB(),
        existing_nullable=False,
    )
    op.create_index("ix_workover_project_pool_measures_gin", "workover_project_pool", ["workover_measures"], unique=False, postgresql_using="gin")
    op.drop_index("ix_data_dictionary_type", table_name="data_dictionary")
    op.drop_table("data_dictionary")
