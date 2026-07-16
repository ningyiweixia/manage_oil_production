from sqlalchemy.orm import Session
from sqlalchemy import func, select, update

from app.core.exceptions import BusinessException
from app.core.security import get_password_hash
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.crud import rbac as crud
from app.models.approval import ApprovalLog
from app.models.rbac import Menu, OperationLog, Permission, Role, User
from app.models.workover import WorkoverProjectPool
from app.schemas.rbac import (
    IsActivePayload,
    MenuCreate,
    MenuOut,
    MenuUpdate,
    PasswordResetPayload,
    PermissionCreate,
    PermissionOut,
    PermissionUpdate,
    RoleBrief,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    SupportMetricOut,
    SystemSupportOverviewOut,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services.auth_service import build_menu_tree, invalidate_user_permission_cache


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        department=user.department,
        mobile=user.mobile,
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        role_ids=[role.id for role in user.roles],
        roles=[RoleBrief(id=role.id, name=role.name, code=role.code) for role in user.roles],
        created_at=user.created_at,
    )


def _role_out(role: Role) -> RoleOut:
    return RoleOut(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        is_active=role.is_active,
        menu_ids=[menu.id for menu in role.menus],
        permission_ids=[permission.id for permission in role.permissions],
    )


def _ensure_all_ids_exist(requested_ids: list[int], found_ids: list[int], label: str) -> None:
    missing_ids = sorted(set(requested_ids) - set(found_ids))
    if missing_ids:
        raise BusinessException(BAD_REQUEST, f"Invalid {label} ids: {missing_ids}")


def create_user(db: Session, payload: UserCreate) -> UserOut:
    if crud.get_user_by_username(db, payload.username):
        raise BusinessException(CONFLICT, "用户名已存在")
    user = User(
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        department=payload.department,
        mobile=payload.mobile,
        email=payload.email,
        is_active=payload.is_active,
        extra_config=payload.extra_config,
    )
    roles = crud.list_roles_by_ids(db, payload.role_ids)
    _ensure_all_ids_exist(payload.role_ids, [role.id for role in roles], "role")
    user.roles = roles
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_out(user)


def update_user(db: Session, user_id: int, payload: UserUpdate) -> UserOut:
    user = crud.get_user(db, user_id)
    if user is None:
        raise BusinessException(BAD_REQUEST, "用户不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    invalidate_user_permission_cache([user.id])
    return _user_out(user)


def set_user_active(db: Session, user_id: int, is_active: bool) -> UserOut:
    user = crud.get_user(db, user_id)
    if user is None:
        raise BusinessException(BAD_REQUEST, "用户不存在")
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    invalidate_user_permission_cache([user.id])
    return _user_out(user)


def reset_user_password(db: Session, user_id: int, payload: PasswordResetPayload) -> UserOut:
    user = crud.get_user(db, user_id)
    if user is None:
        raise BusinessException(BAD_REQUEST, "用户不存在")
    user.hashed_password = get_password_hash(payload.password)
    db.commit()
    db.refresh(user)
    invalidate_user_permission_cache([user.id])
    return _user_out(user)


def assign_user_roles(db: Session, user_id: int, role_ids: list[int]) -> UserOut:
    user = crud.get_user(db, user_id)
    if user is None:
        raise BusinessException(BAD_REQUEST, "用户不存在")
    roles = crud.list_roles_by_ids(db, role_ids)
    _ensure_all_ids_exist(role_ids, [role.id for role in roles], "role")
    user.roles = roles
    db.commit()
    db.refresh(user)
    invalidate_user_permission_cache([user.id])
    return _user_out(user)


def delete_user(db: Session, user_id: int) -> None:
    user = crud.get_user(db, user_id)
    if user is None:
        raise BusinessException(BAD_REQUEST, "用户不存在")
    if user.is_superuser:
        raise BusinessException(BAD_REQUEST, "超级管理员账号不允许删除")
    invalidate_user_permission_cache([user.id])
    db.execute(update(ApprovalLog).where(ApprovalLog.operator_id == user.id).values(operator_id=None))
    db.execute(update(WorkoverProjectPool).where(WorkoverProjectPool.created_by_id == user.id).values(created_by_id=None))
    user.roles.clear()
    db.delete(user)
    db.commit()


def list_users(db: Session) -> list[UserOut]:
    return [_user_out(user) for user in crud.list_users(db)]


def create_role(db: Session, payload: RoleCreate) -> RoleOut:
    role = Role(**payload.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return _role_out(role)


def update_role(db: Session, role_id: int, payload: RoleUpdate) -> RoleOut:
    role = db.get(Role, role_id)
    if role is None:
        raise BusinessException(BAD_REQUEST, "角色不存在")
    for key, value in payload.model_dump().items():
        setattr(role, key, value)
    db.commit()
    db.refresh(role)
    invalidate_user_permission_cache([user.id for user in role.users])
    return _role_out(role)


def assign_role_menus(db: Session, role_id: int, menu_ids: list[int]) -> RoleOut:
    role = db.get(Role, role_id)
    if role is None:
        raise BusinessException(BAD_REQUEST, "角色不存在")
    menus = crud.list_menus_by_ids(db, menu_ids)
    _ensure_all_ids_exist(menu_ids, [menu.id for menu in menus], "menu")
    role.menus = menus
    db.commit()
    db.refresh(role)
    invalidate_user_permission_cache([user.id for user in role.users])
    return _role_out(role)


def assign_role_permissions(db: Session, role_id: int, permission_ids: list[int]) -> RoleOut:
    role = db.get(Role, role_id)
    if role is None:
        raise BusinessException(BAD_REQUEST, "角色不存在")
    permissions = crud.list_permissions_by_ids(db, permission_ids)
    _ensure_all_ids_exist(permission_ids, [permission.id for permission in permissions], "permission")
    role.permissions = permissions
    db.commit()
    db.refresh(role)
    invalidate_user_permission_cache([user.id for user in role.users])
    return _role_out(role)


def delete_role(db: Session, role_id: int) -> None:
    role = db.get(Role, role_id)
    if role is None:
        raise BusinessException(BAD_REQUEST, "角色不存在")
    user_ids = [user.id for user in role.users]
    db.delete(role)
    db.commit()
    invalidate_user_permission_cache(user_ids)


def list_roles(db: Session) -> list[RoleOut]:
    return [_role_out(role) for role in crud.list_roles(db)]


def create_menu(db: Session, payload: MenuCreate) -> MenuOut:
    menu = Menu(**payload.model_dump())
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return MenuOut.model_validate(menu)


def update_menu(db: Session, menu_id: int, payload: MenuUpdate) -> MenuOut:
    menu = db.get(Menu, menu_id)
    if menu is None:
        raise BusinessException(BAD_REQUEST, "菜单不存在")
    for key, value in payload.model_dump().items():
        setattr(menu, key, value)
    db.commit()
    db.refresh(menu)
    return MenuOut.model_validate(menu)


def delete_menu(db: Session, menu_id: int) -> None:
    menu = db.get(Menu, menu_id)
    if menu is None:
        raise BusinessException(BAD_REQUEST, "菜单不存在")
    db.delete(menu)
    db.commit()


def list_menu_tree(db: Session) -> list[MenuOut]:
    return build_menu_tree(crud.list_menus(db))


def create_permission(db: Session, payload: PermissionCreate) -> PermissionOut:
    permission = Permission(**payload.model_dump())
    permission.method = permission.method.upper()
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return PermissionOut.model_validate(permission)


def update_permission(db: Session, permission_id: int, payload: PermissionUpdate) -> PermissionOut:
    permission = db.get(Permission, permission_id)
    if permission is None:
        raise BusinessException(BAD_REQUEST, "权限不存在")
    for key, value in payload.model_dump().items():
        setattr(permission, key, value)
    permission.method = permission.method.upper()
    db.commit()
    db.refresh(permission)
    return PermissionOut.model_validate(permission)


def delete_permission(db: Session, permission_id: int) -> None:
    permission = db.get(Permission, permission_id)
    if permission is None:
        raise BusinessException(BAD_REQUEST, "权限不存在")
    user_ids = [user.id for role in permission.roles for user in role.users]
    db.delete(permission)
    db.commit()
    invalidate_user_permission_cache(user_ids)


def list_permissions(db: Session) -> list[PermissionOut]:
    return [PermissionOut.model_validate(permission) for permission in crud.list_permissions(db)]


def _support_metric(name: str, status: str, value: str | int | float | None, description: str) -> SupportMetricOut:
    return SupportMetricOut(name=name, status=status, value=value, description=description)


def build_system_support_overview(db: Session) -> SystemSupportOverviewOut:
    active_users = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
    active_roles = db.scalar(select(func.count()).select_from(Role).where(Role.is_active.is_(True))) or 0
    active_permissions = db.scalar(select(func.count()).select_from(Permission).where(Permission.is_active.is_(True))) or 0
    recent_errors = (
        db.scalar(
            select(func.count())
            .select_from(OperationLog)
            .where(OperationLog.status_code.is_not(None), OperationLog.status_code >= 40000)
        )
        or 0
    )
    integration_logs = (
        db.scalar(
            select(func.count())
            .select_from(OperationLog)
            .where(
                OperationLog.path.in_(
                    [
                        "/api/v1/a5/sync/trigger",
                        "/api/v1/a5/callback",
                        "/api/v1/reports/statistics-analysis",
                    ]
                )
            )
        )
        or 0
    )

    runtime_monitoring = [
        _support_metric("应用服务", "正常", "FastAPI", "业务接口统一通过 /api/v1 暴露，配合操作日志追踪请求。"),
        _support_metric("数据库连接", "正常", "PostgreSQL/SQLite", "核心业务表、权限表和日志表统一存储。"),
        _support_metric("接口异常", "需关注" if recent_errors else "正常", recent_errors, "统计业务响应码异常的操作日志，用于现场排查。"),
        _support_metric("集成任务", "已纳入", integration_logs, "覆盖 A5 同步、回调和统计分析等跨系统调用留痕。"),
    ]
    security_controls = [
        _support_metric("身份认证", "已启用", "JWT", "兼容后续 SSO/LDAP 接入，当前使用账号密码与 JWT 会话。"),
        _support_metric("角色权限", "已启用", active_roles, "按项目池、审批、运行、物料、统计和运维角色分配菜单与接口权限。"),
        _support_metric("接口安全", "规划中", "Token/签名/IP白名单", "外部系统接口预留 Token、签名和 IP 白名单控制口径。"),
        _support_metric("数据权限", "已启用", active_users, "按部门、角色和项目范围控制业务数据访问边界。"),
    ]
    audit_traceability = [
        _support_metric("操作日志", "已启用", "sys_operation_log", "记录账号、IP、Trace ID、接口、业务码和响应消息。"),
        _support_metric("敏感操作审计", "已纳入", active_permissions, "权限变更、接口配置、统计口径和业务关键动作纳入审计口径。"),
        _support_metric("审批日志", "已启用", "approval_log", "业务审批流转与系统操作日志分层留痕。"),
    ]
    backup_recovery = [
        _support_metric("数据库备份", "策略已定义", "每日增量/每周全量", "核心业务数据库按方案执行增量与全量备份。"),
        _support_metric("附件备份", "策略已定义", "MinIO定期备份", "修前/修后报告、导出文件和业务附件纳入对象存储备份。"),
        _support_metric("恢复预案", "已定义", "数据/附件/配置回滚", "提供数据库恢复、对象文件恢复、配置回滚和服务重启预案。"),
    ]
    message_alerts = [
        _support_metric("审批待办", "已规划", "站内/企业微信", "审批待办、驳回和重提可接入消息提醒。"),
        _support_metric("派工变更", "已规划", "站内/企业微信", "修井运行表派工和进度变化可触发提醒。"),
        _support_metric("物料异常", "已规划", "站内/企业微信", "缺料、配送延迟和异常需求可进入告警队列。"),
        _support_metric("同步失败", "已规划", "站内/企业微信", "A5、承包商和物料平台连续失败后触发告警。"),
    ]
    data_scope = [
        _support_metric("部门范围", "已启用", "department", "非特权用户按所属部门或本人创建数据过滤。"),
        _support_metric("业务角色", "已启用", "RBAC", "不同岗位只看到对应菜单、待办和操作按钮。"),
        _support_metric("项目范围", "可扩展", "project_scope", "预留按负责井号、项目范围和数据来源细分权限。"),
    ]
    return SystemSupportOverviewOut(
        runtime_monitoring=runtime_monitoring,
        security_controls=security_controls,
        audit_traceability=audit_traceability,
        backup_recovery=backup_recovery,
        message_alerts=message_alerts,
        data_scope=data_scope,
    )
