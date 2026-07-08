from typing import Any

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


user_roles = Table(
    "sys_user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("sys_user.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True),
    comment="用户角色关联表",
)


role_menus = Table(
    "sys_role_menu",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True),
    Column("menu_id", Integer, ForeignKey("sys_menu.id", ondelete="CASCADE"), primary_key=True),
    comment="Role-menu association table",
)


role_permissions = Table(
    "sys_role_permission",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("sys_permission.id", ondelete="CASCADE"), primary_key=True),
    comment="角色权限关联表",
)


class User(TimestampMixin, Base):
    __tablename__ = "sys_user"
    __table_args__ = (
        UniqueConstraint("username", name="uq_sys_users_username"),
        {"comment": "系统用户表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(64), nullable=False, comment="登录账号")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    full_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="用户姓名")
    department: Mapped[str | None] = mapped_column(String(128), comment="所属部门")
    mobile: Mapped[str | None] = mapped_column(String(32), comment="Mobile phone")
    email: Mapped[str | None] = mapped_column(String(128), comment="Email")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="Superuser flag")
    extra_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False, comment="JSONB extension config")

    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users", lazy="selectin")
    approval_logs: Mapped[list["ApprovalLog"]] = relationship(back_populates="operator")
    operation_logs: Mapped[list["OperationLog"]] = relationship(back_populates="user")


class Role(TimestampMixin, Base):
    __tablename__ = "sys_role"
    __table_args__ = (
        UniqueConstraint("code", name="uq_sys_roles_code"),
        {"comment": "RBAC角色表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="角色ID")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="角色名称")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="角色编码")
    description: Mapped[str | None] = mapped_column(String(255), comment="角色说明")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="Enabled flag")
    extra_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False, comment="JSONB extension config")

    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")
    menus: Mapped[list["Menu"]] = relationship(secondary=role_menus, back_populates="roles", lazy="selectin")
    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permissions, back_populates="roles", lazy="selectin")


class Menu(TimestampMixin, Base):
    __tablename__ = "sys_menu"
    __table_args__ = (
        Index("ix_sys_menu_parent_id", "parent_id"),
        UniqueConstraint("route_name", name="uq_sys_menu_route_name"),
        {"comment": "System menu and dynamic route table"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="Menu ID")
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("sys_menu.id", ondelete="SET NULL"), comment="Parent menu ID")
    title: Mapped[str] = mapped_column(String(64), nullable=False, comment="Menu title")
    route_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="Frontend route name")
    route_path: Mapped[str] = mapped_column(String(255), nullable=False, comment="Frontend route path")
    component: Mapped[str | None] = mapped_column(String(255), comment="Frontend component")
    icon: Mapped[str | None] = mapped_column(String(64), comment="Icon")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Sort order")
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="Visible flag")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="Enabled flag")
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False, comment="JSONB route meta")

    parent: Mapped["Menu | None"] = relationship(remote_side="Menu.id", back_populates="children")
    children: Mapped[list["Menu"]] = relationship(back_populates="parent")
    roles: Mapped[list[Role]] = relationship(secondary=role_menus, back_populates="menus")


class Permission(TimestampMixin, Base):
    __tablename__ = "sys_permission"
    __table_args__ = (
        UniqueConstraint("code", name="uq_sys_permissions_code"),
        Index("ix_sys_permission_method_path", "method", "path"),
        {"comment": "RBAC权限表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="权限ID")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="权限名称")
    code: Mapped[str] = mapped_column(String(128), nullable=False, comment="权限编码")
    path: Mapped[str] = mapped_column(String(255), nullable=False, comment="资源路径或菜单标识")
    method: Mapped[str] = mapped_column(String(16), nullable=False, comment="动作")
    description: Mapped[str | None] = mapped_column(String(255), comment="Description")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="Enabled flag")
    extra_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False, comment="JSONB extension config")

    roles: Mapped[list[Role]] = relationship(secondary=role_permissions, back_populates="permissions")


class OperationLog(TimestampMixin, Base):
    __tablename__ = "sys_operation_log"
    __table_args__ = (
        Index("ix_sys_operation_log_user_id", "user_id"),
        Index("ix_sys_operation_log_path", "path"),
        {"comment": "System operation log table"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="Operation log ID")
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True, comment="Request trace ID")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id", ondelete="SET NULL"), comment="User ID")
    username: Mapped[str | None] = mapped_column(String(64), comment="Username snapshot")
    ip_address: Mapped[str | None] = mapped_column(String(64), comment="Client IP")
    method: Mapped[str] = mapped_column(String(16), nullable=False, comment="HTTP method")
    path: Mapped[str] = mapped_column(String(255), nullable=False, comment="Request path")
    operation: Mapped[str | None] = mapped_column(String(255), comment="Operation content")
    status_code: Mapped[int | None] = mapped_column(Integer, comment="Business response code")
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, comment="JSONB request payload snapshot")
    response_message: Mapped[str | None] = mapped_column(Text, comment="Response message")

    user: Mapped[User | None] = relationship(back_populates="operation_logs")
