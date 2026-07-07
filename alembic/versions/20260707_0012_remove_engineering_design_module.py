"""Remove engineering design module

Revision ID: 20260707_0012
Revises: 20260707_0011
Create Date: 2026-07-07

"""
from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260707_0012"
down_revision: str | None = "20260707_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_engineering_design_doc_project_id", table_name="engineering_design_doc")
    op.drop_table("engineering_design_doc")


def downgrade() -> None:
    op.create_table(
        "engineering_design_doc",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="文档ID"),
        sa.Column("project_id", sa.Integer(), nullable=True, comment="关联项目池ID"),
        sa.Column("well_no", sa.String(length=64), nullable=False, comment="井号"),
        sa.Column("version", sa.String(length=32), nullable=False, comment="文档版本号"),
        sa.Column("minio_bucket", sa.String(length=128), nullable=False, comment="MinIO桶"),
        sa.Column("minio_object_key", sa.String(length=512), nullable=False, comment="MinIO对象路径"),
        sa.Column("checksum", sa.String(length=128), nullable=True, comment="文件校验值"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["workover_project_pool.id"],
            name=op.f("fk_engineering_design_doc_project_id_workover_project_pool"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_engineering_design_doc")),
        sa.UniqueConstraint("well_no", "version", name="uq_engineering_design_doc_well_version"),
        comment="工程设计文档表",
    )
    op.create_index("ix_engineering_design_doc_project_id", "engineering_design_doc", ["project_id"])
