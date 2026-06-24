from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.dictionary import DataDictionary
from app.models.rbac import Menu, Permission, Role, User


MENU_DEFINITIONS = [
    ("system", None, "系统管理", "system", "/system", "Layout", "settings", 10),
    ("system_users", "system", "用户管理", "system_users", "/system/users", "system/users/index", "user", 11),
    ("system_roles", "system", "角色管理", "system_roles", "/system/roles", "system/roles/index", "shield", 12),
    ("system_menus", "system", "菜单管理", "system_menus", "/system/menus", "system/menus/index", "menu", 13),
    ("system_permissions", "system", "权限管理", "system_permissions", "/system/permissions", "system/permissions/index", "key", 14),
    ("system_dictionaries", "system", "数据字典", "system_dictionaries", "/system/dictionaries", "system/dictionaries/index", "list", 15),
    ("system_logs", "system", "操作日志", "system_logs", "/system/operation-logs", "system/logs/index", "file-text", 16),
    ("workover", None, "上修项目池", "workover", "/workover", "Layout", "database", 20),
    ("workover_project_pool", "workover", "项目池台账", "workover_project_pool", "/workover/project-pools", "workover/project-pools/index", "table", 21),
    ("contractor", None, "承包商管理", "contractor", "/contractor", "Layout", "team", 30),
    ("contractor_capacity", "contractor", "运力报备", "contractor_capacity", "/contractor/capacity", "contractor/capacity/index", "list", 31),
    ("contractor_dispatch", "contractor", "智能派工", "contractor_dispatch", "/contractor/dispatch", "contractor/dispatch/index", "send", 32),
    ("contractor_sheets", "contractor", "修井运行表", "contractor_sheets", "/contractor/operation-sheets", "contractor/operation-sheets/index", "document", 33),
    ("engineering", None, "工程设计管理", "engineering", "/engineering", "Layout", "edit", 40),
    ("engineering_designs", "engineering", "设计文档", "engineering_designs", "/engineering/designs", "engineering/designs/index", "document", 41),
]

PERMISSION_DEFINITIONS = [
    ("system:user:read", "查看用户", "/api/v1/users", "GET"),
    ("system:user:create", "新增用户", "/api/v1/users", "POST"),
    ("system:user:update", "编辑用户", "/api/v1/users/{user_id}", "PUT"),
    ("system:user:delete", "删除用户", "/api/v1/users/{user_id}", "DELETE"),
    ("system:user:assign_roles", "分配用户角色", "/api/v1/users/{user_id}/roles", "PATCH"),
    ("system:role:read", "查看角色", "/api/v1/roles", "GET"),
    ("system:role:create", "新增角色", "/api/v1/roles", "POST"),
    ("system:role:update", "编辑角色", "/api/v1/roles/{role_id}", "PUT"),
    ("system:role:delete", "删除角色", "/api/v1/roles/{role_id}", "DELETE"),
    ("system:role:assign_menus", "分配角色菜单", "/api/v1/roles/{role_id}/menus", "PATCH"),
    ("system:role:assign_permissions", "绑定角色接口权限", "/api/v1/roles/{role_id}/permissions", "PATCH"),
    ("system:menu:read", "查看菜单", "/api/v1/menus", "GET"),
    ("system:menu:create", "新增菜单", "/api/v1/menus", "POST"),
    ("system:menu:update", "编辑菜单", "/api/v1/menus/{menu_id}", "PUT"),
    ("system:menu:delete", "删除菜单", "/api/v1/menus/{menu_id}", "DELETE"),
    ("system:permission:read", "查看接口权限", "/api/v1/permissions", "GET"),
    ("system:permission:create", "新增接口权限", "/api/v1/permissions", "POST"),
    ("system:permission:update", "编辑接口权限", "/api/v1/permissions/{permission_id}", "PUT"),
    ("system:permission:delete", "删除接口权限", "/api/v1/permissions/{permission_id}", "DELETE"),
    ("system:operation_log:read", "查看操作日志", "/api/v1/operation-logs", "GET"),
    ("system:dictionary:read", "查看数据字典", "/api/v1/dictionaries", "GET"),
    ("system:dictionary:manage", "维护数据字典", "/api/v1/dictionaries", "POST"),
    ("workover_project_pool:read", "查看上修项目池", "/api/v1/workover-project-pools", "GET"),
    ("workover_project_pool:create", "新增上修项目池", "/api/v1/workover-project-pools", "POST"),
    ("workover_project_pool:update", "修改上修项目池", "/api/v1/workover-project-pools/{project_id}", "PUT"),
    ("workover_project_pool:delete", "作废上修项目池", "/api/v1/workover-project-pools/{project_id}", "DELETE"),
    ("workover_project_pool:submit", "提报上修项目池", "/api/v1/workover-project-pools/submit", "PATCH"),
    ("workover_project_pool:approve", "审批上修项目池", "/api/v1/workover-project-pools/{project_id}/status", "PATCH"),
    ("workover_project_pool:import", "导入上修项目池", "/api/v1/workover-project-pools/import", "POST"),
    ("workover_project_pool:export", "导出上修项目池", "/api/v1/workover-project-pools/export/all", "GET"),
    ("approval_log:read", "查看审批日志", "/api/v1/approval-logs", "GET"),
    ("rbac:manage", "管理RBAC权限", "/api/v1/rbac", "POST"),
    # 承包商管理权限
    ("contractor:read", "查看承包商运力", "/api/v1/contractors", "GET"),
    ("contractor:create", "报承包商运力", "/api/v1/contractors", "POST"),
    ("contractor:update", "更新承包商运力", "/api/v1/contractors/{contractor_id}", "PUT"),
    ("operation-sheet:read", "查看修井运行表", "/api/v1/contractors/operation-sheets", "GET"),
    ("operation-sheet:create", "创建修井运行表", "/api/v1/contractors/operation-sheets", "POST"),
    ("operation-sheet:dispatch", "派工分配队伍", "/api/v1/contractors/dispatch", "PATCH"),
    ("operation-sheet:update", "更新修井运行表", "/api/v1/contractors/operation-sheets/{sheet_id}/progress", "PATCH"),
    # A5 系统集成权限
    ("a5:sso", "生成A5 SSO令牌", "/api/v1/a5/sso-token", "POST"),
    ("a5:read", "查看A5同步状态", "/api/v1/a5/sync/status", "GET"),
    ("a5:sync", "触发A5数据同步", "/api/v1/a5/sync/trigger", "POST"),
    # 工程设计管理权限
    ("engineering:read", "查看工程设计文档", "/api/v1/engineering-designs", "GET"),
    ("engineering:generate", "生成工程设计文档", "/api/v1/engineering-designs/generate", "POST"),
    ("engineering:delete", "删除工程设计文档", "/api/v1/engineering-designs/{id}", "DELETE"),
]

ROLE_DEFINITIONS = [
    ("super_admin", "超级管理员", "系统内置超级管理员"),
    ("project_pool_admin", "项目池管理员", "负责上修项目池台账维护、提报和导入导出"),
    ("base_entry_clerk", "基层录入员", "负责基层单位上修项目池数据录入"),
    ("business_reviewer", "业务审核员", "负责地质所/工艺所审核"),
    ("contractor_operator", "承包商操作员", "负责队伍运力提报"),
    ("ops_admin", "运维管理员", "负责系统配置与审计"),
]

ROLE_PERMISSION_CODES = {
    "super_admin": {code for code, *_ in PERMISSION_DEFINITIONS},
    "ops_admin": {code for code, *_ in PERMISSION_DEFINITIONS},
    "project_pool_admin": {
        "system:dictionary:read",
        "workover_project_pool:read",
        "workover_project_pool:create",
        "workover_project_pool:update",
        "workover_project_pool:delete",
        "workover_project_pool:submit",
        "workover_project_pool:import",
        "workover_project_pool:export",
        "approval_log:read",
        "operation-sheet:read",
    },
    "base_entry_clerk": {
        "system:dictionary:read",
        "workover_project_pool:read",
        "workover_project_pool:create",
        "workover_project_pool:update",
        "workover_project_pool:import",
    },
    "business_reviewer": {
        "system:dictionary:read",
        "workover_project_pool:read",
        "workover_project_pool:approve",
        "approval_log:read",
        "operation-sheet:read",
        "operation-sheet:dispatch",
        "a5:sso",
        "a5:read",
        "engineering:read",
        "engineering:generate",
    },
    "contractor_operator": {
        "system:dictionary:read",
        "contractor:read",
        "contractor:create",
    },
}


DICTIONARY_DEFINITIONS = [
    ("measure_type", "常规检泵", "pump_repair"),
    ("measure_type", "常规检泵", "常规检泵"),
    ("measure_type", "检泵", "检泵"),
    ("measure_type", "冲砂洗井", "sand_washing"),
    ("measure_type", "冲砂洗井", "冲砂洗井"),
    ("measure_type", "酸化解堵", "acidizing"),
    ("measure_type", "酸化解堵", "酸化解堵"),
    ("measure_type", "酸化", "酸化"),
    ("measure_type", "管柱更换", "tubing_replacement"),
    ("measure_type", "管柱更换", "管柱更换"),
    ("measure_type", "大修作业", "major_workover"),
    ("measure_type", "大修作业", "大修作业"),
    ("measure_type", "热洗清蜡", "热洗清蜡"),
    ("measure_type", "套损治理", "套损治理"),
    ("process_standard", "常规修井工序", "standard_workover"),
    ("well_area", "第一采油作业区", "area_1"),
    ("well_area", "第二采油作业区", "area_2"),
]


def seed() -> None:
    with SessionLocal() as db:
        menus_by_key: dict[str, Menu] = {}
        for key, parent_key, title, route_name, route_path, component, icon, sort_order in MENU_DEFINITIONS:
            menu = db.scalar(select(Menu).where(Menu.route_name == route_name))
            if menu is None:
                menu = Menu(title=title, route_name=route_name, route_path=route_path)
                db.add(menu)
            menu.parent = menus_by_key.get(parent_key) if parent_key else None
            menu.title = title
            menu.route_path = route_path
            menu.component = component
            menu.icon = icon
            menu.sort_order = sort_order
            menu.is_visible = True
            menu.is_active = True
            menus_by_key[key] = menu

        permissions_by_code: dict[str, Permission] = {}
        for code, name, path, method in PERMISSION_DEFINITIONS:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, name=name, path=path, method=method)
                db.add(permission)
            permission.name = name
            permission.path = path
            permission.method = method
            permission.is_active = True
            permissions_by_code[code] = permission

        for dict_type, item_label, item_value in DICTIONARY_DEFINITIONS:
            item = db.scalar(
                select(DataDictionary).where(
                    DataDictionary.dict_type == dict_type,
                    DataDictionary.item_value == item_value,
                )
            )
            if item is None:
                item = DataDictionary(dict_type=dict_type, item_value=item_value, item_label=item_label)
                db.add(item)
            item.item_label = item_label
            item.is_active = True

        roles_by_code: dict[str, Role] = {}
        for code, name, description in ROLE_DEFINITIONS:
            role = db.scalar(select(Role).where(Role.code == code))
            if role is None:
                role = Role(code=code, name=name)
                db.add(role)
            role.name = name
            role.description = description
            role.is_active = True
            role.permissions = [permissions_by_code[item] for item in sorted(ROLE_PERMISSION_CODES[code])]
            roles_by_code[code] = role

        roles_by_code["super_admin"].menus = list(menus_by_key.values())
        roles_by_code["ops_admin"].menus = list(menus_by_key.values())
        roles_by_code["project_pool_admin"].menus = [menus_by_key["workover"], menus_by_key["workover_project_pool"]]
        roles_by_code["base_entry_clerk"].menus = [menus_by_key["workover"], menus_by_key["workover_project_pool"]]
        roles_by_code["business_reviewer"].menus = [
            menus_by_key["workover"], menus_by_key["workover_project_pool"],
            menus_by_key["contractor"], menus_by_key["contractor_dispatch"], menus_by_key["contractor_sheets"],
            menus_by_key["engineering"], menus_by_key["engineering_designs"],
        ]
        roles_by_code["contractor_operator"].menus = [
            menus_by_key["contractor"], menus_by_key["contractor_capacity"],
        ]

        admin = db.scalar(select(User).where(User.username == "admin"))
        if admin is None:
            if not settings.admin_initial_password:
                raise RuntimeError("ADMIN_INITIAL_PASSWORD must be set before creating the initial admin user")
            admin = User(
                username="admin",
                hashed_password=get_password_hash(settings.admin_initial_password),
                full_name="系统管理员",
                department="运维中心",
                is_active=True,
                is_superuser=True,
            )
            db.add(admin)
        admin.is_active = True
        admin.is_superuser = True
        admin.roles = [roles_by_code["super_admin"]]
        db.commit()


if __name__ == "__main__":
    seed()
