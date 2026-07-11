"""Contractor capacity external sync fields

Revision ID: 20260710_0014
Revises: 20260708_0002
Create Date: 2026-07-10

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260710_0014"
down_revision: str | None = "20260708_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    json_default = sa.text("'{}'") if is_sqlite else sa.text("'{}'::jsonb")
    contractor_columns = [
        sa.Column("external_system_id", sa.String(128), nullable=True, comment="外部承包商系统队伍ID"),
        sa.Column("external_status", sa.String(64), nullable=True, comment="外部系统原始状态"),
        sa.Column("source_type", sa.Enum("EXTERNAL_SYNC", "LOCAL_SUPPLEMENT", "SYNC_ERROR", native_enum=False, length=32), nullable=False, server_default="LOCAL_SUPPLEMENT", comment="数据来源"),
        sa.Column("sync_status", sa.Enum("SYNCED", "PENDING_CONFIRM", "CONFLICT", "INVALID", native_enum=False, length=32), nullable=False, server_default="PENDING_CONFIRM", comment="同步状态"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True, comment="最近同步时间"),
        sa.Column("sync_error_message", sa.Text(), nullable=True, comment="同步异常信息"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True, comment="人工确认时间"),
        sa.Column("confirmed_by_id", sa.Integer(), nullable=True, comment="确认人ID"),
        sa.Column("contact_name", sa.String(64), nullable=True, comment="联系人"),
        sa.Column("contact_phone", sa.String(32), nullable=True, comment="联系电话"),
        sa.Column("qualification_expire_at", sa.Date(), nullable=True, comment="资质有效期"),
        sa.Column("equipment_summary", sa.Text(), nullable=True, comment="设备概况"),
    ]
    if is_sqlite:
        with op.batch_alter_table("contractor_capacity") as batch_op:
            for column in contractor_columns:
                batch_op.add_column(column)
            batch_op.create_foreign_key("fk_contractor_capacity_confirmed_by_id_sys_user", "sys_user", ["confirmed_by_id"], ["id"], ondelete="SET NULL")
            batch_op.create_index("ix_contractor_capacity_external_system_id", ["external_system_id"])
            batch_op.create_index("ix_contractor_capacity_source_type", ["source_type"])
            batch_op.create_index("ix_contractor_capacity_sync_status", ["sync_status"])
            batch_op.create_unique_constraint("uq_contractor_capacity_external_daily", ["external_system_id", "report_date"])
    else:
        for column in contractor_columns:
            op.add_column("contractor_capacity", column)
        op.create_foreign_key("fk_contractor_capacity_confirmed_by_id_sys_user", "contractor_capacity", "sys_user", ["confirmed_by_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_contractor_capacity_external_system_id", "contractor_capacity", ["external_system_id"])
        op.create_index("ix_contractor_capacity_source_type", "contractor_capacity", ["source_type"])
        op.create_index("ix_contractor_capacity_sync_status", "contractor_capacity", ["sync_status"])
        op.create_unique_constraint("uq_contractor_capacity_external_daily", "contractor_capacity", ["external_system_id", "report_date"])

    op.create_table(
        "contractor_capacity_sync_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="同步日志ID"),
        sa.Column("sync_type", sa.Enum("SCHEDULED", "MANUAL", "SINGLE_TEAM", native_enum=False, length=32), nullable=False, comment="同步方式"),
        sa.Column("status", sa.Enum("SUCCESS", "FAILED", "PARTIAL", native_enum=False, length=32), nullable=False, comment="同步结果"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, comment="开始时间"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="结束时间"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0", comment="成功数量"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0", comment="失败数量"),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0", comment="新增数量"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0", comment="更新数量"),
        sa.Column("ignored_count", sa.Integer(), nullable=False, server_default="0", comment="忽略数量"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column("operator_id", sa.Integer(), nullable=True, comment="操作人ID"),
        sa.Column("raw_summary", json_type, nullable=False, server_default=json_default, comment="原始摘要"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["operator_id"], ["sys_user.id"], name="fk_contractor_capacity_sync_log_operator_id_sys_user", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contractor_capacity_sync_log")),
        comment="承包商运力同步日志表",
    )
    op.create_index("ix_contractor_capacity_sync_log_started_at", "contractor_capacity_sync_log", ["started_at"])
    op.create_index("ix_contractor_capacity_sync_log_status", "contractor_capacity_sync_log", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    op.drop_index("ix_contractor_capacity_sync_log_status", table_name="contractor_capacity_sync_log")
    op.drop_index("ix_contractor_capacity_sync_log_started_at", table_name="contractor_capacity_sync_log")
    op.drop_table("contractor_capacity_sync_log")
    columns = [
        "equipment_summary",
        "qualification_expire_at",
        "contact_phone",
        "contact_name",
        "confirmed_by_id",
        "confirmed_at",
        "sync_error_message",
        "last_synced_at",
        "sync_status",
        "source_type",
        "external_status",
        "external_system_id",
    ]
    if is_sqlite:
        with op.batch_alter_table("contractor_capacity") as batch_op:
            batch_op.drop_constraint("uq_contractor_capacity_external_daily", type_="unique")
            batch_op.drop_index("ix_contractor_capacity_sync_status")
            batch_op.drop_index("ix_contractor_capacity_source_type")
            batch_op.drop_index("ix_contractor_capacity_external_system_id")
            batch_op.drop_constraint("fk_contractor_capacity_confirmed_by_id_sys_user", type_="foreignkey")
            for column in columns:
                batch_op.drop_column(column)
    else:
        op.drop_constraint("uq_contractor_capacity_external_daily", "contractor_capacity", type_="unique")
        op.drop_index("ix_contractor_capacity_sync_status", table_name="contractor_capacity")
        op.drop_index("ix_contractor_capacity_source_type", table_name="contractor_capacity")
        op.drop_index("ix_contractor_capacity_external_system_id", table_name="contractor_capacity")
        op.drop_constraint("fk_contractor_capacity_confirmed_by_id_sys_user", "contractor_capacity", type_="foreignkey")
        for column in columns:
            op.drop_column("contractor_capacity", column)
