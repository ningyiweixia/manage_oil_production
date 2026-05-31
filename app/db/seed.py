from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.rbac import Permission, Role, User


ROLE_DEFINITIONS = [
    ("project_pool_admin", "项目池管理员", "负责上修项目池维护"),
    ("business_reviewer", "业务审核员", "负责地质所/工艺所审核"),
    ("contractor_operator", "承包商操作员", "负责队伍运力提报"),
    ("ops_admin", "运维管理员", "负责系统配置与审计"),
]

PERMISSION_DEFINITIONS = [
    ("workover_project_pool:read", "查看上修项目池", "/api/v1/workover-projects", "read"),
    ("workover_project_pool:write", "维护上修项目池", "/api/v1/workover-projects", "write"),
    ("approval_log:read", "查看审批日志", "/api/v1/approval-logs", "read"),
    ("rbac:manage", "管理RBAC权限", "/api/v1/rbac", "manage"),
]


def seed() -> None:
    with SessionLocal() as db:
        permissions: list[Permission] = []
        for code, name, resource, action in PERMISSION_DEFINITIONS:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, name=name, resource=resource, action=action)
                db.add(permission)
            permissions.append(permission)

        roles: list[Role] = []
        for code, name, description in ROLE_DEFINITIONS:
            role = db.scalar(select(Role).where(Role.code == code))
            if role is None:
                role = Role(code=code, name=name, description=description)
                db.add(role)
            role.permissions = permissions
            roles.append(role)

        admin = db.scalar(select(User).where(User.username == "admin"))
        if admin is None:
            admin = User(
                username="admin",
                hashed_password=get_password_hash("ChangeMe_123!"),
                full_name="系统管理员",
                department="运维中心",
                is_active=True,
            )
            db.add(admin)
        admin.roles = roles
        db.commit()


if __name__ == "__main__":
    seed()
