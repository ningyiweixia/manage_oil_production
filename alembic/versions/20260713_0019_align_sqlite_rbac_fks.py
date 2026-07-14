"""align SQLite RBAC foreign keys and permission column types

Revision ID: 20260713_0019
Revises: 20260713_0018
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260713_0019"
down_revision: str | None = "20260713_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _foreign_key_name(table_name: str, column_name: str) -> str | None:
    for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys(table_name):
        if foreign_key.get("constrained_columns") == [column_name]:
            return foreign_key.get("name")
    return None


def upgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return

    approval_fk = _foreign_key_name("approval_log", "operator_id")
    with op.batch_alter_table("approval_log", recreate="always") as batch_op:
        if approval_fk:
            batch_op.drop_constraint(approval_fk, type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_approval_log_operator_id_sys_user",
            "sys_user",
            ["operator_id"],
            ["id"],
            ondelete="SET NULL",
        )

    project_fk = _foreign_key_name("workover_project_pool", "created_by_id")
    with op.batch_alter_table("workover_project_pool", recreate="always") as batch_op:
        if project_fk:
            batch_op.drop_constraint(project_fk, type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_workover_project_pool_created_by_id_sys_user",
            "sys_user",
            ["created_by_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("sys_permission", recreate="always") as batch_op:
        batch_op.alter_column(
            "path",
            existing_type=sa.String(length=128),
            type_=sa.String(length=255),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "method",
            existing_type=sa.String(length=32),
            type_=sa.String(length=16),
            existing_nullable=False,
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return

    with op.batch_alter_table("sys_permission", recreate="always") as batch_op:
        batch_op.alter_column(
            "path",
            existing_type=sa.String(length=255),
            type_=sa.String(length=128),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "method",
            existing_type=sa.String(length=16),
            type_=sa.String(length=32),
            existing_nullable=False,
        )

    project_fk = _foreign_key_name("workover_project_pool", "created_by_id")
    with op.batch_alter_table("workover_project_pool", recreate="always") as batch_op:
        if project_fk:
            batch_op.drop_constraint(project_fk, type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_workover_project_pool_created_by_id_sys_users",
            "sys_user",
            ["created_by_id"],
            ["id"],
        )

    approval_fk = _foreign_key_name("approval_log", "operator_id")
    with op.batch_alter_table("approval_log", recreate="always") as batch_op:
        if approval_fk:
            batch_op.drop_constraint(approval_fk, type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_approval_log_operator_id_sys_users",
            "sys_user",
            ["operator_id"],
            ["id"],
        )
