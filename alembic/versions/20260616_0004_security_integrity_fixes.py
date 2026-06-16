"""security and integrity fixes

Revision ID: 20260616_0004
Revises: 20260604_0003
Create Date: 2026-06-16 00:00:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260616_0004"
down_revision: Union[str, None] = "20260604_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APPROVAL_ACTION_VALUES = ("CREATE", "UPDATE", "DELETE", "VOID", "SUBMIT", "APPROVE", "REJECT", "ROLLBACK")


def upgrade() -> None:
    op.create_check_constraint(
        "ck_workover_operation_sheet_progress_range",
        "workover_operation_sheet",
        "progress >= 0 AND progress <= 100",
    )
    op.create_index("ix_approval_log_operator_id", "approval_log", ["operator_id"], unique=False)

    # Existing installs used a varchar-backed enum; widen the check set when the
    # database has a generated enum constraint name.
    op.execute(
        """
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT conname INTO constraint_name
            FROM pg_constraint
            WHERE conrelid = 'approval_log'::regclass
              AND contype = 'c'
              AND pg_get_constraintdef(oid) LIKE '%action%';

            IF constraint_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE approval_log DROP CONSTRAINT %I', constraint_name);
            END IF;

            ALTER TABLE approval_log
            ADD CONSTRAINT ck_approval_log_action
            CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'VOID', 'SUBMIT', 'APPROVE', 'REJECT', 'ROLLBACK'));
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE approval_log DROP CONSTRAINT IF EXISTS ck_approval_log_action")
    op.drop_index("ix_approval_log_operator_id", table_name="approval_log")
    op.drop_constraint("ck_workover_operation_sheet_progress_range", "workover_operation_sheet", type_="check")
