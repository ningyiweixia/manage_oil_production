"""init core tables

Revision ID: 20260531_0001
Revises:
Create Date: 2026-05-31 22:50:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260531_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb_type():
    """Return the correct JSON column type for the current dialect."""
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "sys_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="权限ID"),
        sa.Column("name", sa.String(length=64), nullable=False, comment="权限名称"),
        sa.Column("code", sa.String(length=128), nullable=False, comment="权限编码"),
        sa.Column("resource", sa.String(length=128), nullable=False, comment="资源路径或菜单标识"),
        sa.Column("action", sa.String(length=32), nullable=False, comment="动作"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_permissions")),
        sa.UniqueConstraint("code", name="uq_sys_permissions_code"),
        comment="RBAC权限表",
    )
    op.create_table(
        "sys_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="角色ID"),
        sa.Column("name", sa.String(length=64), nullable=False, comment="角色名称"),
        sa.Column("code", sa.String(length=64), nullable=False, comment="角色编码"),
        sa.Column("description", sa.String(length=255), nullable=True, comment="角色说明"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_roles")),
        sa.UniqueConstraint("code", name="uq_sys_roles_code"),
        comment="RBAC角色表",
    )
    op.create_table(
        "sys_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="用户ID"),
        sa.Column("username", sa.String(length=64), nullable=False, comment="登录账号"),
        sa.Column("hashed_password", sa.String(length=255), nullable=False, comment="密码哈希"),
        sa.Column("full_name", sa.String(length=64), nullable=False, comment="用户姓名"),
        sa.Column("department", sa.String(length=128), nullable=True, comment="所属部门"),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否启用"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_users")),
        sa.UniqueConstraint("username", name="uq_sys_users_username"),
        comment="系统用户表",
    )
    op.create_table(
        "contractor_capacity",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="运力ID"),
        sa.Column("contractor_name", sa.String(length=128), nullable=False, comment="承包商名称"),
        sa.Column("team_name", sa.String(length=128), nullable=False, comment="队伍名称"),
        sa.Column("report_date", sa.Date(), nullable=False, comment="日报日期"),
        sa.Column("available_count", sa.Integer(), nullable=False, comment="可用队伍数"),
        sa.Column("status", sa.Enum("AVAILABLE", "BUSY", "OFFLINE", native_enum=False, length=32), nullable=False, comment="队伍状态"),
        sa.Column("capability_tags", _jsonb_type(), nullable=False, comment="特定施工能力标签JSONB"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contractor_capacity")),
        comment="承包商运力表",
    )
    op.create_index("ix_contractor_capacity_report_date", "contractor_capacity", ["report_date"], unique=False)
    op.create_table(
        "sys_role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["sys_permissions.id"], name=op.f("fk_sys_role_permissions_permission_id_sys_permissions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["sys_roles.id"], name=op.f("fk_sys_role_permissions_role_id_sys_roles"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name=op.f("pk_sys_role_permissions")),
        comment="角色权限关联表",
    )
    op.create_table(
        "sys_user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["sys_roles.id"], name=op.f("fk_sys_user_roles_role_id_sys_roles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["sys_users.id"], name=op.f("fk_sys_user_roles_user_id_sys_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id", name=op.f("pk_sys_user_roles")),
        comment="用户角色关联表",
    )
    op.create_table(
        "workover_project_pool",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="项目池ID"),
        sa.Column("well_no", sa.String(length=64), nullable=False, comment="井号"),
        sa.Column("block_name", sa.String(length=128), nullable=True, comment="区块"),
        sa.Column("report_unit", sa.String(length=128), nullable=False, comment="提报单位"),
        sa.Column("production_priority", sa.Integer(), nullable=False, comment="产量优先级"),
        sa.Column("status", sa.Enum("DRAFT", "PENDING_GEOLOGY_VERIFY", "PENDING_PROCESS_VERIFY", "APPROVED", "REJECTED", "DISPATCHED", native_enum=False, length=64), nullable=False, comment="项目状态"),
        sa.Column("reason", sa.Text(), nullable=True, comment="上修原因"),
        sa.Column("workover_measures", _jsonb_type(), nullable=False, comment="修井措施JSONB"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True, comment="审批通过时间"),
        sa.Column("created_by_id", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["created_by_id"], ["sys_users.id"], name=op.f("fk_workover_project_pool_created_by_id_sys_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workover_project_pool")),
        comment="上修项目池表",
    )
    op.create_index("ix_workover_project_pool_well_no", "workover_project_pool", ["well_no"], unique=False)
    if op.get_bind().dialect.name != "sqlite":
        op.create_index("ix_workover_project_pool_measures_gin", "workover_project_pool", ["workover_measures"], unique=False, postgresql_using="gin")
    else:
        op.create_index("ix_workover_project_pool_measures_gin", "workover_project_pool", ["workover_measures"], unique=False)
    op.create_table(
        "approval_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="审批日志ID"),
        sa.Column("business_type", sa.String(length=64), nullable=False, comment="业务类型"),
        sa.Column("business_id", sa.Integer(), nullable=False, comment="业务主键ID"),
        sa.Column("node_code", sa.String(length=64), nullable=False, comment="审批节点编码"),
        sa.Column("action", sa.Enum("SUBMIT", "APPROVE", "REJECT", "ROLLBACK", native_enum=False, length=32), nullable=False, comment="审批动作"),
        sa.Column("comment", sa.Text(), nullable=True, comment="审批意见"),
        sa.Column("operator_id", sa.Integer(), nullable=False, comment="操作人ID"),
        sa.Column("operator_ip", sa.String(length=64), nullable=True, comment="操作人IP"),
        sa.Column("before_snapshot", _jsonb_type(), nullable=True, comment="变更前数据快照"),
        sa.Column("after_snapshot", _jsonb_type(), nullable=True, comment="变更后数据快照"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["operator_id"], ["sys_users.id"], name=op.f("fk_approval_log_operator_id_sys_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_log")),
        comment="审批日志表",
    )
    op.create_index("ix_approval_log_business", "approval_log", ["business_type", "business_id"], unique=False)
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
        sa.ForeignKeyConstraint(["project_id"], ["workover_project_pool.id"], name=op.f("fk_engineering_design_doc_project_id_workover_project_pool"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_engineering_design_doc")),
        sa.UniqueConstraint("well_no", "version", name="uq_engineering_design_doc_well_version"),
        comment="工程设计文档表",
    )
    op.create_table(
        "workover_operation_sheet",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="运行表ID"),
        sa.Column("project_id", sa.Integer(), nullable=False, comment="项目池ID"),
        sa.Column("contractor_capacity_id", sa.Integer(), nullable=True, comment="承包商运力ID"),
        sa.Column("operation_no", sa.String(length=64), nullable=False, comment="作业编号"),
        sa.Column("status", sa.Enum("WAITING_DISPATCH", "DISPATCHED", "WORKING", "FINISHED", "CANCELED", native_enum=False, length=64), nullable=False, comment="作业状态"),
        sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True, comment="计划开始时间"),
        sa.Column("planned_end_at", sa.DateTime(timezone=True), nullable=True, comment="计划结束时间"),
        sa.Column("actual_start_at", sa.DateTime(timezone=True), nullable=True, comment="实际开始时间"),
        sa.Column("actual_end_at", sa.DateTime(timezone=True), nullable=True, comment="实际结束时间"),
        sa.Column("progress", sa.Integer(), nullable=False, comment="施工进度百分比"),
        sa.Column("progress_detail", _jsonb_type(), nullable=False, comment="施工进度明细JSONB"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["contractor_capacity_id"], ["contractor_capacity.id"], name=op.f("fk_workover_operation_sheet_contractor_capacity_id_contractor_capacity"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["workover_project_pool.id"], name=op.f("fk_workover_operation_sheet_project_id_workover_project_pool"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workover_operation_sheet")),
        sa.UniqueConstraint("operation_no", name=op.f("uq_workover_operation_sheet_operation_no")),
        comment="修井运行表",
    )
    op.create_index("ix_workover_operation_sheet_status", "workover_operation_sheet", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workover_operation_sheet_status", table_name="workover_operation_sheet")
    op.drop_table("workover_operation_sheet")
    op.drop_table("engineering_design_doc")
    op.drop_index("ix_approval_log_business", table_name="approval_log")
    op.drop_table("approval_log")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_index("ix_workover_project_pool_measures_gin", table_name="workover_project_pool", postgresql_using="gin")
    else:
        op.drop_index("ix_workover_project_pool_measures_gin", table_name="workover_project_pool")
    op.drop_index("ix_workover_project_pool_well_no", table_name="workover_project_pool")
    op.drop_table("workover_project_pool")
    op.drop_table("sys_user_roles")
    op.drop_table("sys_role_permissions")
    op.drop_index("ix_contractor_capacity_report_date", table_name="contractor_capacity")
    op.drop_table("contractor_capacity")
    op.drop_table("sys_users")
    op.drop_table("sys_roles")
    op.drop_table("sys_permissions")
