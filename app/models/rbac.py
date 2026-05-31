from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


user_roles = Table(
    "sys_user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("sys_roles.id", ondelete="CASCADE"), primary_key=True),
    comment="用户角色关联表",
)


role_permissions = Table(
    "sys_role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("sys_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("sys_permissions.id", ondelete="CASCADE"), primary_key=True),
    comment="角色权限关联表",
)


class User(TimestampMixin, Base):
    __tablename__ = "sys_users"
    __table_args__ = (UniqueConstraint("username", name="uq_sys_users_username"), {"comment": "系统用户表"})

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(64), nullable=False, comment="登录账号")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    full_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="用户姓名")
    department: Mapped[str | None] = mapped_column(String(128), comment="所属部门")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")

    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users", lazy="selectin")
    approval_logs: Mapped[list["ApprovalLog"]] = relationship(back_populates="operator")


class Role(TimestampMixin, Base):
    __tablename__ = "sys_roles"
    __table_args__ = (UniqueConstraint("code", name="uq_sys_roles_code"), {"comment": "RBAC角色表"})

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="角色ID")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="角色名称")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="角色编码")
    description: Mapped[str | None] = mapped_column(String(255), comment="角色说明")

    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )


class Permission(TimestampMixin, Base):
    __tablename__ = "sys_permissions"
    __table_args__ = (UniqueConstraint("code", name="uq_sys_permissions_code"), {"comment": "RBAC权限表"})

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="权限ID")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="权限名称")
    code: Mapped[str] = mapped_column(String(128), nullable=False, comment="权限编码")
    resource: Mapped[str] = mapped_column(String(128), nullable=False, comment="资源路径或菜单标识")
    action: Mapped[str] = mapped_column(String(32), nullable=False, comment="动作")

    roles: Mapped[list[Role]] = relationship(secondary=role_permissions, back_populates="permissions")
