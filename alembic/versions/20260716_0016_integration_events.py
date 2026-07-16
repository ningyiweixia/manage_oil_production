"""create durable integration event table

Revision ID: 20260716_0016_integration_events
Revises: 20260711_0015_analytics_alerts
Create Date: 2026-07-16 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260716_0016_integration_events"
down_revision = "20260711_0015_analytics_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_event",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("event_key", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="RECEIVED"),
        sa.Column("operation_no", sa.String(length=64), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("source", "event_key", name="uq_integration_event_source_key"),
    )
    op.create_index("ix_integration_event_source_status", "integration_event", ["source", "status"])
    op.create_index("ix_integration_event_operation_no", "integration_event", ["operation_no"])


def downgrade() -> None:
    op.drop_index("ix_integration_event_operation_no", table_name="integration_event")
    op.drop_index("ix_integration_event_source_status", table_name="integration_event")
    op.drop_table("integration_event")
