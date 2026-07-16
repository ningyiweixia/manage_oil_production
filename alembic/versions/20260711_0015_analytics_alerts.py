"""create analytics alert table

Revision ID: 20260711_0015_analytics_alerts
Revises: 20260710_0014
Create Date: 2026-07-11 00:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260711_0015_analytics_alerts"
down_revision = "20260710_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_alert",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("alert_key", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("source_module", sa.String(length=64), nullable=False),
        sa.Column("business_type", sa.String(length=64), nullable=True),
        sa.Column("business_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("assignee_id", sa.Integer(), sa.ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assignee_name", sa.String(length=64), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_by_id", sa.Integer(), sa.ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("closed_by_id", sa.Integer(), sa.ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("alert_key", name="uq_analytics_alert_alert_key"),
        sa.CheckConstraint("status in ('OPEN', 'PROCESSING', 'CLOSED')", name="ck_analytics_alert_status"),
        sa.CheckConstraint("severity in ('low', 'medium', 'high')", name="ck_analytics_alert_severity"),
        sa.Index("ix_analytics_alert_status", "status"),
        sa.Index("ix_analytics_alert_assignee_id", "assignee_id"),
        comment="统计分析告警表",
    )


def downgrade() -> None:
    op.drop_table("analytics_alert")
