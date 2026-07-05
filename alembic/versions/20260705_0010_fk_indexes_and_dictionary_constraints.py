"""Add FK indexes and dictionary constraints (code review fixes)

- Add FK index for engineering_design_doc.project_id
- Add FK index for workover_operation_sheet.project_id
- Add FK index for workover_project_pool.created_by_id
- Add unique constraint on data_dictionary (dict_type, item_label)
- Add FK index for workover_operation_sheet.contractor_capacity_id

Revision ID: 20260705_0010
Revises: 20260705_0009
Create Date: 2026-07-05

"""
from typing import Sequence

from alembic import op

revision: str = "20260705_0010"
down_revision: str | None = "20260705_0009"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 添加缺失的外键索引
    op.create_index("ix_engineering_design_doc_project_id", "engineering_design_doc", ["project_id"])
    op.create_index("ix_workover_operation_sheet_project_id", "workover_operation_sheet", ["project_id"])
    op.create_index("ix_workover_operation_sheet_contractor_capacity_id", "workover_operation_sheet", ["contractor_capacity_id"])
    op.create_index("ix_workover_project_pool_created_by_id", "workover_project_pool", ["created_by_id"])

    # 添加数据字典 item_label 唯一约束 (同 dict_type 内 label 唯一)
    op.create_unique_constraint(
        "uq_data_dictionary_type_label",
        "data_dictionary",
        ["dict_type", "item_label"],
    )

    # 添加承包商运力每日唯一约束 (同一队伍每天只能报备一次)
    op.create_unique_constraint(
        "uq_contractor_capacity_team_daily",
        "contractor_capacity",
        ["contractor_name", "team_name", "report_date"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_contractor_capacity_team_daily", "contractor_capacity", type_="unique")
    op.drop_constraint("uq_data_dictionary_type_label", "data_dictionary", type_="unique")
    op.drop_index("ix_workover_project_pool_created_by_id", table_name="workover_project_pool")
    op.drop_index("ix_workover_operation_sheet_contractor_capacity_id", table_name="workover_operation_sheet")
    op.drop_index("ix_workover_operation_sheet_project_id", table_name="workover_operation_sheet")
    op.drop_index("ix_engineering_design_doc_project_id", table_name="engineering_design_doc")
