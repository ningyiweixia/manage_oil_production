"""support physical user deletion

Revision ID: 20260629_0005
Revises: 20260616_0004
Create Date: 2026-06-29 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260629_0005"
down_revision: Union[str, None] = "20260616_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    is_sqlite = op.get_bind().dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("approval_log") as batch_op:
            batch_op.alter_column("operator_id", existing_type=sa.Integer(), nullable=True)
        return

    op.execute(
        """
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            FOR constraint_name IN
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'approval_log'::regclass
                  AND contype = 'f'
                  AND (SELECT attnum FROM pg_attribute WHERE attrelid = 'approval_log'::regclass AND attname = 'operator_id') = ANY(conkey)
            LOOP
                EXECUTE format('ALTER TABLE approval_log DROP CONSTRAINT %I', constraint_name);
            END LOOP;

            ALTER TABLE approval_log ALTER COLUMN operator_id DROP NOT NULL;
            ALTER TABLE approval_log
                ADD CONSTRAINT fk_approval_log_operator_id_sys_user
                FOREIGN KEY (operator_id) REFERENCES sys_user(id) ON DELETE SET NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            FOR constraint_name IN
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'workover_project_pool'::regclass
                  AND contype = 'f'
                  AND (SELECT attnum FROM pg_attribute WHERE attrelid = 'workover_project_pool'::regclass AND attname = 'created_by_id') = ANY(conkey)
            LOOP
                EXECUTE format('ALTER TABLE workover_project_pool DROP CONSTRAINT %I', constraint_name);
            END LOOP;

            ALTER TABLE workover_project_pool
                ADD CONSTRAINT fk_workover_project_pool_created_by_id_sys_user
                FOREIGN KEY (created_by_id) REFERENCES sys_user(id) ON DELETE SET NULL;
        END $$;
        """
    )


def downgrade() -> None:
    is_sqlite = op.get_bind().dialect.name == "sqlite"

    if is_sqlite:
        return

    op.execute("ALTER TABLE approval_log DROP CONSTRAINT IF EXISTS fk_approval_log_operator_id_sys_user")
    op.execute(
        """
        ALTER TABLE approval_log
            ADD CONSTRAINT fk_approval_log_operator_id_sys_user
            FOREIGN KEY (operator_id) REFERENCES sys_user(id)
        """
    )
    op.execute("ALTER TABLE workover_project_pool DROP CONSTRAINT IF EXISTS fk_workover_project_pool_created_by_id_sys_user")
    op.execute(
        """
        ALTER TABLE workover_project_pool
            ADD CONSTRAINT fk_workover_project_pool_created_by_id_sys_user
            FOREIGN KEY (created_by_id) REFERENCES sys_user(id)
        """
    )
