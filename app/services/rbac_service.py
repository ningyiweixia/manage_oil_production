from sqlalchemy.orm import Session
from sqlalchemy import update

from app.core.exceptions import BusinessException
from app.core.security import get_password_hash
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.crud import rbac as crud
from app.models.approval import ApprovalLog
from app.models.rbac import Menu, Permission, Role, User
from app.models.workover import WorkoverProjectPool
from app.schemas.rbac import (
    MenuCreate,
    MenuOut,
    MenuUpdate,
    PermissionCreate,
    PermissionOut,
    PermissionUpdate,
    RoleCreate,
    RoleOut,
    RoleUpdate,
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
