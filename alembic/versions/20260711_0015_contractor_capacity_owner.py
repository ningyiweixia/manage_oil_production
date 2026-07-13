"""Add contractor capacity owner

Revision ID: 20260711_0015
Revises: 20260710_0014
Create Date: 2026-07-11

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260711_0015"
down_revision: str | None = "20260710_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    if is_sqlite:
        with op.batch_alter_table("contractor_capacity") as batch_op:
            batch_op.add_column(sa.Column("created_by_id", sa.Integer(), nullable=True, comment="创建人ID"))
            batch_op.create_foreign_key(
                "fk_contractor_capacity_created_by_id_sys_user",
                "sys_user",
                ["created_by_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_index("ix_contractor_capacity_created_by_id", ["created_by_id"])
    else:
        op.add_column("contractor_capacity", sa.Column("created_by_id", sa.Integer(), nullable=True, comment="创建人ID"))
        op.create_foreign_key(
            "fk_contractor_capacity_created_by_id_sys_user",
            "contractor_capacity",
            "sys_user",
            ["created_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_contractor_capacity_created_by_id", "contractor_capacity", ["created_by_id"])

    # Preserve visibility of legacy local reports by assigning them to the
    # bootstrap administrator rather than leaving an ownerless hidden row.
    op.execute(
        "UPDATE contractor_capacity SET created_by_id = "
        "(SELECT id FROM sys_user WHERE is_superuser = true ORDER BY id LIMIT 1) "
        "WHERE created_by_id IS NULL"
    )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    if is_sqlite:
        with op.batch_alter_table("contractor_capacity") as batch_op:
            batch_op.drop_index("ix_contractor_capacity_created_by_id")
            batch_op.drop_constraint("fk_contractor_capacity_created_by_id_sys_user", type_="foreignkey")
            batch_op.drop_column("created_by_id")
    else:
        op.drop_index("ix_contractor_capacity_created_by_id", table_name="contractor_capacity")
        op.drop_constraint("fk_contractor_capacity_created_by_id_sys_user", "contractor_capacity", type_="foreignkey")
        op.drop_column("contractor_capacity", "created_by_id")
