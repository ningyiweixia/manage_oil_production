from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.rbac import Permission, Role, User


ROLE_DEFINITIONS = [
    ("project_pool_admin", "项目池管理员", "负责上修项目池台账维护、提报和导入导出"),
    ("base_entry_clerk", "基层录入员", "负责基层单位上修项目池数据录入"),
    ("business_reviewer", "业务审核员", "负责地质所/工艺所审核"),
    ("contractor_operator", "承包商操作员", "负责队伍运力提报"),
    ("ops_admin", "运维管理员", "负责系统配置与审计"),
]

PERMISSION_DEFINITIONS = [
    ("workover_project_pool:read", "查看上修项目池", "/api/v1/workover-project-pools", "read"),
    ("workover_project_pool:create", "新增上修项目池", "/api/v1/workover-project-pools", "create"),
    ("workover_project_pool:update", "修改上修项目池", "/api/v1/workover-project-pools", "update"),
    ("workover_project_pool:delete", "作废上修项目池", "/api/v1/workover-project-pools", "delete"),
    ("workover_project_pool:submit", "提报上修项目池", "/api/v1/workover-project-pools/submit", "submit"),
    ("workover_project_pool:approve", "审批上修项目池", "/api/v1/workover-project-pools/*/status", "approve"),
    ("workover_project_pool:import", "导入上修项目池", "/api/v1/workover-project-pools/import", "import"),
    ("workover_project_pool:export", "导出上修项目池", "/api/v1/workover-project-pools/export/all", "export"),
    ("approval_log:read", "查看审批日志", "/api/v1/approval-logs", "read"),
    ("rbac:manage", "管理RBAC权限", "/api/v1/rbac", "manage"),
]

ROLE_PERMISSION_CODES = {
    "project_pool_admin": {
        "workover_project_pool:read",
        "workover_project_pool:create",
        "workover_project_pool:update",
        "workover_project_pool:delete",
        "workover_project_pool:submit",
        "workover_project_pool:import",
        "workover_project_pool:export",
        "approval_log:read",
    },
    "base_entry_clerk": {
        "workover_project_pool:read",
        "workover_project_pool:create",
        "workover_project_pool:update",
        "workover_project_pool:import",
    },
    "business_reviewer": {
        "workover_project_pool:read",
        "workover_project_pool:approve",
        "approval_log:read",
    },
    "contractor_operator": set(),
    "ops_admin": {code for code, *_ in PERMISSION_DEFINITIONS},
}


def seed() -> None:
    with SessionLocal() as db:
        permissions_by_code: dict[str, Permission] = {}
        for code, name, resource, action in PERMISSION_DEFINITIONS:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, name=name, resource=resource, action=action)
                db.add(permission)
            permissions_by_code[code] = permission

        roles: list[Role] = []
        for code, name, description in ROLE_DEFINITIONS:
            role = db.scalar(select(Role).where(Role.code == code))
            if role is None:
                role = Role(code=code, name=name, description=description)
                db.add(role)
            role.permissions = [
                permissions_by_code[permission_code]
                for permission_code in sorted(ROLE_PERMISSION_CODES[code])
            ]
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
