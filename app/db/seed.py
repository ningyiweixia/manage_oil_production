from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.dictionary import DataDictionary
from app.models.rbac import Menu, Permission, Role, User
from app.models.workover import WorkoverProjectPool


MENU_DEFINITIONS = [
    ("system", None, "系统管理", "system", "/system", "Layout", "settings", 10),
    ("system_account", "system", "账号设置", "system_account", "/system/account", "system/account/index", "user", 11),
    ("system_users", "system", "用户管理", "system_users", "/system/users", "system/users/index", "user", 12),
    ("system_roles", "system", "角色管理", "system_roles", "/system/roles", "system/roles/index", "shield", 13),
    ("system_menus", "system", "菜单管理", "system_menus", "/system/menus", "system/menus/index", "menu", 14),
    ("system_permissions", "system", "权限管理", "system_permissions", "/system/permissions", "system/permissions/index", "key", 15),
    ("system_dictionaries", "system", "数据字典", "system_dictionaries", "/system/dictionaries", "system/dictionaries/index", "list", 16),
    ("system_logs", "system", "操作日志", "system_logs", "/system/operation-logs", "system/logs/index", "file-text", 17),
    ("workover_project_pool", None, "项目池台账", "workover_project_pool", "/workover/project-pools", "workover/project-pools/index", "table", 20),
    ("analytics", None, "统计分析", "analytics", "/dashboard", "analytics/dashboard", "trend-charts", 25),
    ("contractor", None, "承包商管理", "contractor", "/contractor", "Layout", "team", 30),
    ("contractor_capacity", "contractor", "运力报备", "contractor_capacity", "/contractor/capacity", "contractor/capacity/index", "list", 31),
    ("contractor_dispatch", "contractor", "智能派工", "contractor_dispatch", "/contractor/dispatch", "contractor/dispatch/index", "send", 32),
    ("contractor_sheets", "contractor", "修井运行表", "contractor_sheets", "/contractor/operation-sheets", "contractor/operation-sheets/index", "document", 33),
    ("material", None, "物料管理", "material", "/material", "Layout", "goods", 35),
    ("material_requirements", "material", "物料需求", "material_requirements", "/material/requirements", "material/requirements/index", "list", 36),
    ("material_delivery", "material", "物料配送", "material_delivery", "/material/delivery", "material/delivery/index", "truck", 37),
    ("a5", None, "A5 系统集成", "a5", "/a5/integration", "a5/integration", "monitor", 50),
    ("completion", None, "完井台账", "completion", "/completion", "completion/index", "document", 45),
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
    # 物料管理权限
    ("material:read", "查看物料需求", "/api/v1/materials", "GET"),
    ("material:create", "创建物料需求", "/api/v1/materials", "POST"),
    ("material:update", "更新物料需求", "/api/v1/materials/{req_id}", "PUT"),
    ("material:delete", "删除物料需求", "/api/v1/materials/{req_id}", "DELETE"),
    # 完井台账权限
    ("completion:read", "查看完井台账", "/api/v1/well-completions", "GET"),
    ("completion:create", "创建完井记录", "/api/v1/well-completions", "POST"),
    ("completion:update", "更新完井记录", "/api/v1/well-completions/{record_id}", "PUT"),
    ("completion:delete", "删除完井记录", "/api/v1/well-completions/{record_id}", "DELETE"),
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
        "material:read",
        "completion:read",
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
        "material:read",
        "completion:read",
        "completion:create",
    },
    "contractor_operator": {
        "system:dictionary:read",
        "contractor:read",
        "contractor:create",
        "material:read",
        "material:create",
    },
}


DICTIONARY_DEFINITIONS = [
    ("dictionary_type", "字典类型", "dictionary_type"),
    ("dictionary_type", "修井措施类型", "measure_type"),
    ("dictionary_type", "工序标准", "process_standard"),
    ("dictionary_type", "井区/作业区", "well_area"),
    ("dictionary_type", "上修项目池状态", "project_pool_status"),
    ("dictionary_type", "修井运行状态", "operation_status"),
    ("dictionary_type", "承包商运力状态", "contractor_capacity_status"),
    ("dictionary_type", "审批动作", "approval_action"),
    ("dictionary_type", "业务类型", "business_type"),
    ("dictionary_type", "生产优先级", "production_priority"),
    ("dictionary_type", "HTTP 请求方法", "http_method"),
    ("dictionary_type", "业务响应码", "business_status_code"),
    ("dictionary_type", "系统角色", "system_role"),
    ("dictionary_type", "系统菜单", "system_menu"),
    ("dictionary_type", "外部系统", "external_system"),
    ("measure_type", "常规检泵", "pump_repair"),
    ("measure_type", "检泵", "pump_inspection"),
    ("measure_type", "冲砂洗井", "sand_washing"),
    ("measure_type", "酸化解堵", "acidizing"),
    ("measure_type", "管柱更换", "tubing_replacement"),
    ("measure_type", "大修作业", "major_workover"),
    ("measure_type", "热洗清蜡", "hot_wax_washing"),
    ("measure_type", "套损治理", "casing_damage_treatment"),
    ("process_standard", "常规修井工序", "standard_workover"),
    ("well_area", "第一采油作业区", "area_1"),
    ("well_area", "第二采油作业区", "area_2"),
    ("project_pool_status", "草稿", "DRAFT"),
    ("project_pool_status", "待地质核实", "PENDING_GEOLOGY_VERIFY"),
    ("project_pool_status", "待工艺核实", "PENDING_PROCESS_VERIFY"),
    ("project_pool_status", "已通过", "APPROVED"),
    ("project_pool_status", "已驳回", "REJECTED"),
    ("project_pool_status", "已派工", "DISPATCHED"),
    ("operation_status", "待派工", "WAITING_DISPATCH"),
    ("operation_status", "已派工", "DISPATCHED"),
    ("operation_status", "施工中", "WORKING"),
    ("operation_status", "已完工", "FINISHED"),
    ("operation_status", "已取消", "CANCELED"),
    ("contractor_capacity_status", "可用", "AVAILABLE"),
    ("contractor_capacity_status", "忙碌", "BUSY"),
    ("contractor_capacity_status", "离线", "OFFLINE"),
    ("approval_action", "创建", "CREATE"),
    ("approval_action", "更新", "UPDATE"),
    ("approval_action", "删除", "DELETE"),
    ("approval_action", "作废", "VOID"),
    ("approval_action", "提交", "SUBMIT"),
    ("approval_action", "审批通过", "APPROVE"),
    ("approval_action", "驳回", "REJECT"),
    ("approval_action", "回退", "ROLLBACK"),
    ("business_type", "上修项目池", "workover_project_pool"),
    ("business_type", "承包商运力", "contractor_capacity"),
    ("business_type", "修井运行表", "workover_operation_sheet"),
    ("business_type", "A5 系统集成", "a5_integration"),
    ("production_priority", "低优先级", "1"),
    ("production_priority", "中优先级", "3"),
    ("production_priority", "高优先级", "5"),
    ("production_priority", "紧急优先级", "10"),
    ("http_method", "读取", "GET"),
    ("http_method", "创建", "POST"),
    ("http_method", "全量更新", "PUT"),
    ("http_method", "局部更新", "PATCH"),
    ("http_method", "删除", "DELETE"),
    ("business_status_code", "成功", "20000"),
    ("business_status_code", "请求参数错误", "40001"),
    ("business_status_code", "未认证", "40100"),
    ("business_status_code", "无权限", "40300"),
    ("business_status_code", "并发或唯一性冲突", "40900"),
    ("business_status_code", "请求过于频繁", "42900"),
    ("business_status_code", "数据库不可用", "50300"),
    ("business_status_code", "A5 系统连接失败", "60001"),
    ("system_role", "超级管理员", "super_admin"),
    ("system_role", "项目池管理员", "project_pool_admin"),
    ("system_role", "基层录入员", "base_entry_clerk"),
    ("system_role", "业务审核员", "business_reviewer"),
    ("system_role", "承包商操作员", "contractor_operator"),
    ("system_role", "运维管理员", "ops_admin"),
    ("system_menu", "系统管理", "system"),
    ("system_menu", "用户管理", "system_users"),
    ("system_menu", "角色管理", "system_roles"),
    ("system_menu", "菜单管理", "system_menus"),
    ("system_menu", "权限管理", "system_permissions"),
    ("system_menu", "数据字典", "system_dictionaries"),
    ("system_menu", "操作日志", "system_logs"),
    ("system_menu", "项目池台账", "workover_project_pool"),
    ("system_menu", "统计分析", "analytics"),
    ("system_menu", "承包商管理", "contractor"),
    ("system_menu", "A5 系统集成", "a5"),
    ("material_status", "待处理", "PENDING"),
    ("material_status", "已审核", "APPROVED"),
    ("material_status", "已计划", "PLANNED"),
    ("material_status", "已出库", "DELIVERED"),
    ("material_status", "已到场", "ARRIVED"),
    ("material_status", "已使用", "USED"),
    ("material_status", "已取消", "CANCELED"),
    ("material_requirement_type", "正常需求", "NORMAL"),
    ("material_requirement_type", "紧急需求", "EMERGENCY"),
    ("external_system", "A5 系统", "a5"),
    ("external_system", "企业微信告警", "wecom_alert"),
]

MEASURE_TYPE_VALUE_ALIASES = {
    "常规检泵": "pump_repair",
    "检泵": "pump_inspection",
    "冲砂洗井": "sand_washing",
    "酸化解堵": "acidizing",
    "酸化": "acidizing",
    "管柱更换": "tubing_replacement",
    "大修作业": "major_workover",
    "热洗清蜡": "hot_wax_washing",
    "套损治理": "casing_damage_treatment",
}

STALE_DICTIONARY_ITEMS = [
    ("system_menu", "workover"),
    ("system_menu", "engineering"),
    ("business_type", "engineering_design_doc"),
    ("business_status_code", "60002"),
    ("external_system", "fpm"),
    ("external_system", "minio"),
]

STALE_MENU_ROUTE_NAMES = {"workover", "engineering", "engineering_designs"}
STALE_PERMISSION_CODES = {"engineering:read", "engineering:generate", "engineering:delete"}


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

        stale_menus = db.scalars(select(Menu).where(Menu.route_name.in_(STALE_MENU_ROUTE_NAMES))).all()
        for menu in stale_menus:
            menu.roles.clear()
            db.delete(menu)

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
        stale_permissions = db.scalars(select(Permission).where(Permission.code.in_(STALE_PERMISSION_CODES))).all()
        for permission in stale_permissions:
            permission.roles.clear()
            db.delete(permission)

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

        stale_measure_items = db.scalars(
            select(DataDictionary).where(
                DataDictionary.dict_type == "measure_type",
                DataDictionary.item_value.in_(MEASURE_TYPE_VALUE_ALIASES.keys()),
            )
        ).all()
        for item in stale_measure_items:
            db.delete(item)
        for dict_type, item_value in STALE_DICTIONARY_ITEMS:
            item = db.scalar(
                select(DataDictionary).where(
                    DataDictionary.dict_type == dict_type,
                    DataDictionary.item_value == item_value,
                )
            )
            if item is not None:
                db.delete(item)

        for project in db.scalars(select(WorkoverProjectPool)).all():
            measures_jsonb = project.measures_jsonb or {}
            measures = measures_jsonb.get("measures", [])
            if not isinstance(measures, list):
                continue
            changed = False
            next_measures = []
            for measure in measures:
                if isinstance(measure, dict):
                    measure = dict(measure)
                    raw_type = measure.get("measure_type")
                    if isinstance(raw_type, str) and raw_type in MEASURE_TYPE_VALUE_ALIASES:
                        measure["measure_type"] = MEASURE_TYPE_VALUE_ALIASES[raw_type]
                        changed = True
                next_measures.append(measure)
            if changed:
                project.measures_jsonb = {**measures_jsonb, "measures": next_measures}

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
        roles_by_code["project_pool_admin"].menus = [menus_by_key["workover_project_pool"], menus_by_key["analytics"], menus_by_key["material"], menus_by_key["material_requirements"], menus_by_key["completion"]]
        roles_by_code["base_entry_clerk"].menus = [menus_by_key["workover_project_pool"]]
        roles_by_code["business_reviewer"].menus = [
            menus_by_key["workover_project_pool"],
            menus_by_key["contractor"], menus_by_key["contractor_dispatch"], menus_by_key["contractor_sheets"],
            menus_by_key["analytics"], menus_by_key["a5"],
            menus_by_key["material"], menus_by_key["material_requirements"],
            menus_by_key["completion"],
        ]
        roles_by_code["contractor_operator"].menus = [
            menus_by_key["contractor"], menus_by_key["contractor_capacity"],
            menus_by_key["material"], menus_by_key["material_requirements"], menus_by_key["material_delivery"],
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
