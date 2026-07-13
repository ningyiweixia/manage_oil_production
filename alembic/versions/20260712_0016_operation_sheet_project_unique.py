"""Enforce one operation sheet per project.

Revision ID: 20260712_0016
Revises: 20260711_0015
Create Date: 2026-07-12
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260712_0016"
down_revision: str | None = "20260711_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    # Historical versions allowed duplicate sheets. Keep the most advanced one
    # (then the earliest ID), move dependent material/completion records to it,
    # and retain audit rows as historical evidence of the retired sheet IDs.
    duplicates = bind.execute(
        sa.text(
            "SELECT project_id FROM workover_operation_sheet "
            "GROUP BY project_id HAVING COUNT(*) > 1"
        )
    ).scalars().all()
    rank = {"FINISHED": 4, "WORKING": 3, "DISPATCHED": 2, "WAITING_DISPATCH": 1, "CANCELED": 0}
    for project_id in duplicates:
        rows = bind.execute(
            sa.text(
                "SELECT id, status, contractor_capacity_id FROM workover_operation_sheet WHERE project_id = :project_id ORDER BY id"
            ),
            {"project_id": project_id},
        ).mappings().all()
        keep_id = max(rows, key=lambda row: (rank.get(str(row["status"]), -1), -int(row["id"])))["id"]
        retired_ids = [row["id"] for row in rows if row["id"] != keep_id]
        for row in rows:
            if row["id"] == keep_id:
                continue
            retired_id = row["id"]
            if row["status"] in {"DISPATCHED", "WORKING"} and row["contractor_capacity_id"] is not None:
                bind.execute(
                    sa.text(
                        "UPDATE contractor_capacity SET available_count = available_count + 1, "
                        "status = CASE WHEN status IN ('OFFLINE', 'EXCEPTION') THEN status ELSE 'AVAILABLE' END "
                        "WHERE id = :contractor_id"
                    ),
                    {"contractor_id": row["contractor_capacity_id"]},
                )
            bind.execute(sa.text("UPDATE material_requirement SET operation_sheet_id = :keep_id WHERE operation_sheet_id = :retired_id"), {"keep_id": keep_id, "retired_id": retired_id})
            bind.execute(sa.text("UPDATE well_completion_record SET operation_sheet_id = :keep_id WHERE operation_sheet_id = :retired_id"), {"keep_id": keep_id, "retired_id": retired_id})
            bind.execute(sa.text("DELETE FROM workover_operation_sheet WHERE id = :retired_id"), {"retired_id": retired_id})
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("workover_operation_sheet") as batch_op:
            batch_op.create_unique_constraint("uq_workover_operation_sheet_project", ["project_id"])
    else:
        op.create_unique_constraint(
            "uq_workover_operation_sheet_project", "workover_operation_sheet", ["project_id"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("workover_operation_sheet") as batch_op:
            batch_op.drop_constraint("uq_workover_operation_sheet_project", type_="unique")
    else:
        op.drop_constraint("uq_workover_operation_sheet_project", "workover_operation_sheet", type_="unique")
