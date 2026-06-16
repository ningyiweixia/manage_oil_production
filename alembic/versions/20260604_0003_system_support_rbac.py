"""system support rbac module

Revision ID: 20260604_0003
Revises: 20260602_0002
Create Date: 2026-06-04 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260604_0003"
down_revision: Union[str, None] = "20260602_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("sys_users", "sys_user")
    op.rename_table("sys_roles", "sys_role")
    op.rename_table("sys_permissions", "sys_permission")
    op.rename_table("sys_user_roles", "sys_user_role")
    op.rename_table("sys_role_permissions", "sys_role_permission")

    op.alter_column("sys_permission", "resource", new_column_name="path", existing_type=sa.String(length=128), existing_nullable=False)
    op.alter_column("sys_permission", "action", new_column_name="method", existing_type=sa.String(length=32), existing_nullable=False)
    op.execute("UPDATE sys_permission SET method = upper(method)")
    op.alter_column("sys_permission", "path", type_=sa.String(length=255), existing_type=sa.String(length=128), existing_nullable=False)
    op.alter_column("sys_permission", "method", type_=sa.String(length=16), existing_type=sa.String(length=32), existing_nullable=False)

    op.add_column("sys_user", sa.Column("mobile", sa.String(length=32), nullable=True, comment="Mobile phone"))
    op.add_column("sys_user", sa.Column("email", sa.String(length=128), nullable=True, comment="Email"))
    op.add_column("sys_user", sa.Column("is_superuser", sa.Boolean(), server_default=sa.false(), nullable=False, comment="Superuser flag"))
    op.add_column("sys_user", sa.Column("extra_config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False, comment="JSONB extension config"))

    op.add_column("sys_role", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False, comment="Enabled flag"))
    op.add_column("sys_role", sa.Column("extra_config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False, comment="JSONB extension config"))

    op.add_column("sys_permission", sa.Column("description", sa.String(length=255), nullable=True, comment="Description"))
    op.add_column("sys_permission", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False, comment="Enabled flag"))
    op.add_column("sys_permission", sa.Column("extra_config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False, comment="JSONB extension config"))

    op.create_table(
        "sys_menu",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="Menu ID"),
        sa.Column("parent_id", sa.Integer(), nullable=True, comment="Parent menu ID"),
        sa.Column("title", sa.String(length=64), nullable=False, comment="Menu title"),
        sa.Column("route_name", sa.String(length=128), nullable=False, comment="Frontend route name"),
        sa.Column("route_path", sa.String(length=255), nullable=False, comment="Frontend route path"),
        sa.Column("component", sa.String(length=255), nullable=True, comment="Frontend component"),
        sa.Column("icon", sa.String(length=64), nullable=True, comment="Icon"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="Sort order"),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true(), comment="Visible flag"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true(), comment="Enabled flag"),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="JSONB route meta"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["parent_id"], ["sys_menu.id"], name=op.f("fk_sys_menu_parent_id_sys_menu"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_menu")),
        sa.UniqueConstraint("route_name", name="uq_sys_menu_route_name"),
        comment="System menu and dynamic route table",
    )
    op.create_index("ix_sys_menu_parent_id", "sys_menu", ["parent_id"], unique=False)

    op.create_table(
        "sys_role_menu",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("menu_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["menu_id"], ["sys_menu.id"], name=op.f("fk_sys_role_menu_menu_id_sys_menu"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["sys_role.id"], name=op.f("fk_sys_role_menu_role_id_sys_role"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "menu_id", name=op.f("pk_sys_role_menu")),
        comment="Role-menu association table",
    )

    op.create_table(
        "sys_operation_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="Operation log ID"),
        sa.Column("user_id", sa.Integer(), nullable=True, comment="User ID"),
        sa.Column("username", sa.String(length=64), nullable=True, comment="Username snapshot"),
        sa.Column("ip_address", sa.String(length=64), nullable=True, comment="Client IP"),
        sa.Column("method", sa.String(length=16), nullable=False, comment="HTTP method"),
        sa.Column("path", sa.String(length=255), nullable=False, comment="Request path"),
        sa.Column("operation", sa.String(length=255), nullable=True, comment="Operation content"),
        sa.Column("status_code", sa.Integer(), nullable=True, comment="Business response code"),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="JSONB request payload snapshot"),
        sa.Column("response_message", sa.Text(), nullable=True, comment="Response message"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["sys_user.id"], name=op.f("fk_sys_operation_log_user_id_sys_user"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_operation_log")),
        comment="System operation log table",
    )
    op.create_index("ix_sys_operation_log_user_id", "sys_operation_log", ["user_id"], unique=False)
    op.create_index("ix_sys_operation_log_path", "sys_operation_log", ["path"], unique=False)
    op.create_index("ix_sys_permission_method_path", "sys_permission", ["method", "path"], unique=False)

    op.execute("UPDATE sys_user SET is_superuser = true WHERE username = 'admin'")


def downgrade() -> None:
    op.drop_index("ix_sys_permission_method_path", table_name="sys_permission")
    op.drop_index("ix_sys_operation_log_path", table_name="sys_operation_log")
    op.drop_index("ix_sys_operation_log_user_id", table_name="sys_operation_log")
    op.drop_table("sys_operation_log")
    op.drop_table("sys_role_menu")
    op.drop_index("ix_sys_menu_parent_id", table_name="sys_menu")
    op.drop_table("sys_menu")
    op.drop_column("sys_permission", "extra_config")
    op.drop_column("sys_permission", "is_active")
    op.drop_column("sys_permission", "description")
    op.drop_column("sys_role", "extra_config")
    op.drop_column("sys_role", "is_active")
    op.drop_column("sys_user", "extra_config")
    op.drop_column("sys_user", "is_superuser")
    op.drop_column("sys_user", "email")
    op.drop_column("sys_user", "mobile")
    op.alter_column("sys_permission", "method", type_=sa.String(length=32), existing_type=sa.String(length=16), existing_nullable=False)
    op.alter_column("sys_permission", "path", type_=sa.String(length=128), existing_type=sa.String(length=255), existing_nullable=False)
    op.alter_column("sys_permission", "method", new_column_name="action", existing_type=sa.String(length=32), existing_nullable=False)
    op.alter_column("sys_permission", "path", new_column_name="resource", existing_type=sa.String(length=128), existing_nullable=False)
    op.rename_table("sys_role_permission", "sys_role_permissions")
    op.rename_table("sys_user_role", "sys_user_roles")
    op.rename_table("sys_permission", "sys_permissions")
    op.rename_table("sys_role", "sys_roles")
    op.rename_table("sys_user", "sys_users")
