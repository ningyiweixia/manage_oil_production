from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.redis import cache_client
from app.core.security import create_token, decode_token_payload, verify_password
from app.core.status_codes import FORBIDDEN, UNAUTHORIZED
from app.crud.rbac import get_user, get_user_by_username
from app.models.rbac import Menu, Permission, Role, User
from app.schemas.auth import CurrentUserOut, LoginResponse, TokenResponse
from app.schemas.rbac import MenuOut, PermissionOut, RoleOut


ACCESS_REVOKE_PREFIX = "auth:access:revoked:"
REFRESH_TOKEN_PREFIX = "auth:refresh:"


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


def build_menu_tree(menus: list[Menu]) -> list[MenuOut]:
    nodes = {
        menu.id: MenuOut.model_validate(menu).model_copy(update={"children": []})
        for menu in sorted(menus, key=lambda item: (item.sort_order, item.id))
        if menu.is_active and menu.is_visible
    }
    roots: list[MenuOut] = []
    for menu in sorted(menus, key=lambda item: (item.sort_order, item.id)):
        if menu.id not in nodes:
            continue
        node = nodes[menu.id]
        if menu.parent_id and menu.parent_id in nodes:
            nodes[menu.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


def user_permissions(user: User) -> list[Permission]:
    permissions = {
        permission.id: permission
        for role in user.roles
        if user.is_superuser or role.is_active
        for permission in role.permissions
        if permission.is_active
    }
    return sorted(permissions.values(), key=lambda item: item.code)


def user_menus(user: User) -> list[Menu]:
    menus = {
        menu.id: menu
        for role in user.roles
        if role.is_active
        for menu in role.menus
        if menu.is_active
    }
    return sorted(menus.values(), key=lambda item: (item.sort_order, item.id))


def get_user_permission_codes(db: Session, user_id: int) -> set[str]:
    cache_key = f"rbac:user:{user_id}:permissions"
    cached = cache_client.get_json(cache_key)
    if cached is not None:
        return set(cached)
    user = get_user(db, user_id)
    if user is None or not user.is_active:
        raise BusinessException(UNAUTHORIZED, "身份失效")
    codes = {permission.code for permission in user_permissions(user)}
    if user.is_superuser:
        codes.add("*")
    cache_client.set_json(cache_key, sorted(codes), expire_seconds=300)
    return codes


def invalidate_user_permission_cache(user_ids: list[int]) -> None:
    for user_id in user_ids:
        cache_client.delete(f"rbac:user:{user_id}:permissions")


def authenticate_user(db: Session, username: str, password: str) -> User:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        raise BusinessException(UNAUTHORIZED, "用户名或密码错误")
    if not user.is_active:
        raise BusinessException(FORBIDDEN, "账号已停用")
    return user


def issue_login_response(user: User) -> LoginResponse:
    access_token, _ = create_token(
        str(user.id),
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token, refresh_jti = create_token(
        str(user.id),
        "refresh",
        timedelta(minutes=settings.refresh_token_expire_minutes),
    )
    cache_client.set_json(
        f"{REFRESH_TOKEN_PREFIX}{refresh_jti}",
        {"user_id": user.id},
        expire_seconds=settings.refresh_token_expire_minutes * 60,
    )
    permissions = user_permissions(user)
    menus = build_menu_tree(user_menus(user))
    return LoginResponse(
        token=TokenResponse(access_token=access_token, refresh_token=refresh_token),
        user=CurrentUserOut(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            department=user.department,
            roles=[_role_out(role) for role in user.roles],
            permissions=[PermissionOut.model_validate(permission) for permission in permissions],
            menus=menus,
        ),
        permissions=[permission.code for permission in permissions],
        menus=menus,
    )


def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
    payload = decode_token_payload(refresh_token)
    if payload.get("typ") != "refresh":
        raise BusinessException(UNAUTHORIZED, "刷新令牌无效")
    jti = payload.get("jti")
    if not jti or cache_client.get_json(f"{REFRESH_TOKEN_PREFIX}{jti}") is None:
        raise BusinessException(UNAUTHORIZED, "刷新令牌已失效")
    user = get_user(db, int(payload["sub"]))
    if user is None or not user.is_active:
        raise BusinessException(UNAUTHORIZED, "身份失效")
    access_token, _ = create_token(
        str(user.id),
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def _seconds_until_exp(payload: dict) -> int:
    exp = payload.get("exp")
    if not exp:
        return settings.access_token_expire_minutes * 60
    return max(int(exp - datetime.now(timezone.utc).timestamp()), 1)


def is_access_token_revoked(jti: str | None) -> bool:
    return bool(jti and cache_client.get_json(f"{ACCESS_REVOKE_PREFIX}{jti}") is not None)


def revoke_access_token(access_token: str | None) -> None:
    if not access_token:
        return
    try:
        payload = decode_token_payload(access_token)
    except BusinessException:
        return
    if payload.get("typ") != "access":
        return
    jti = payload.get("jti")
    if jti:
        cache_client.set_json(
            f"{ACCESS_REVOKE_PREFIX}{jti}",
            {"sub": payload.get("sub")},
            expire_seconds=_seconds_until_exp(payload),
        )


def logout_token(refresh_token: str | None, access_token: str | None = None) -> None:
    revoke_access_token(access_token)
    if not refresh_token:
        return
    try:
        payload = decode_token_payload(refresh_token)
    except BusinessException:
        return
    jti = payload.get("jti")
    if jti:
        cache_client.delete(f"{REFRESH_TOKEN_PREFIX}{jti}")


def get_user_permissions(user: User) -> set[str]:
    return {permission.code for permission in user_permissions(user)}
