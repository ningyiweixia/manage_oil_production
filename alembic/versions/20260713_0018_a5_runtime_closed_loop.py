"""complete A5 runtime closed loop

Revision ID: 20260713_0018
Revises: 20260712_0017, 20260711_0015_analytics_alerts
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260713_0018"
down_revision: tuple[str, str] = ("20260712_0017", "20260711_0015_analytics_alerts")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    json_default = sa.text("'{}'") if is_sqlite else sa.text("'{}'::jsonb")
    bind.execute(sa.text("UPDATE contractor_capacity SET available_count = 0 WHERE available_count < 0"))
    if is_sqlite:
        with op.batch_alter_table("contractor_capacity") as batch_op:
            batch_op.create_unique_constraint(
                "uq_contractor_capacity_team_daily",
                ["contractor_name", "team_name", "report_date"],
            )
            batch_op.create_check_constraint(
                "ck_contractor_capacity_available_count_nonnegative",
                "available_count >= 0",
            )
    else:
        op.create_check_constraint(
            "ck_contractor_capacity_available_count_nonnegative",
            "contractor_capacity",
            "available_count >= 0",
        )
    op.add_column("workover_operation_sheet", sa.Column("last_a5_report_date", sa.Date(), nullable=True, comment="最近A5上修日报日期"))
    op.add_column("workover_operation_sheet", sa.Column("a5_sync_result", sa.String(length=32), nullable=True, comment="最近A5同步结果"))
    op.add_column("workover_operation_sheet", sa.Column("a5_sync_error", sa.Text(), nullable=True, comment="最近A5同步失败原因"))

    op.create_table(
        "a5_sync_batch",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sync_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_operation_no", sa.String(length=64), nullable=True),
        sa.Column("sync_cursor", sa.String(length=255), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unchanged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("not_found_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_summary", json_type, nullable=False, server_default=json_default),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        comment="A5数据同步批次表",
    )
    op.create_index("ix_a5_sync_batch_started_at", "a5_sync_batch", ["started_at"])
    op.create_index("ix_a5_sync_batch_status", "a5_sync_batch", ["status"])

    op.create_table(
        "a5_daily_report_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("operation_sheet_id", sa.Integer(), nullable=True),
        sa.Column("operation_no", sa.String(length=64), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("external_event_id", sa.String(length=128), nullable=True),
        sa.Column("external_version", sa.Integer(), nullable=True),
        sa.Column("a5_status", sa.String(length=64), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("matched", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("raw_payload", json_type, nullable=False, server_default=json_default),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["batch_id"], ["a5_sync_batch.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["operation_sheet_id"], ["workover_operation_sheet.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", name="uq_a5_daily_report_fingerprint"),
        comment="A5上修日报同步记录表",
    )
    op.create_index("ix_a5_daily_report_operation_no", "a5_daily_report_record", ["operation_no"])
    op.create_index("ix_a5_daily_report_report_date", "a5_daily_report_record", ["report_date"])
    op.create_index("ix_a5_daily_report_batch_id", "a5_daily_report_record", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_a5_daily_report_batch_id", table_name="a5_daily_report_record")
    op.drop_index("ix_a5_daily_report_report_date", table_name="a5_daily_report_record")
    op.drop_index("ix_a5_daily_report_operation_no", table_name="a5_daily_report_record")
    op.drop_table("a5_daily_report_record")
    op.drop_index("ix_a5_sync_batch_status", table_name="a5_sync_batch")
    op.drop_index("ix_a5_sync_batch_started_at", table_name="a5_sync_batch")
    op.drop_table("a5_sync_batch")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("contractor_capacity") as batch_op:
            batch_op.drop_constraint("ck_contractor_capacity_available_count_nonnegative", type_="check")
            batch_op.drop_constraint("uq_contractor_capacity_team_daily", type_="unique")
    else:
        op.drop_constraint(
            "ck_contractor_capacity_available_count_nonnegative",
            "contractor_capacity",
            type_="check",
        )
    op.drop_column("workover_operation_sheet", "a5_sync_error")
    op.drop_column("workover_operation_sheet", "a5_sync_result")
    op.drop_column("workover_operation_sheet", "last_a5_report_date")
