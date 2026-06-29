from collections import defaultdict, deque
from time import monotonic

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import BusinessException
from app.core.security import get_password_hash, verify_password
from app.core.status_codes import BAD_REQUEST, TOO_MANY_REQUESTS, UNAUTHORIZED
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.auth import AccountCancelRequest, ChangePasswordRequest, CurrentUserOut, LoginRequest, LoginResponse, RefreshTokenRequest, TokenResponse
from app.schemas.response import ApiResponse, success
from app.schemas.rbac import PermissionOut, RoleOut
from app.services import rbac_service
from app.services.auth_service import (
    authenticate_user,
    build_menu_tree,
    issue_login_response,
    logout_token,
    refresh_access_token,
    user_menus,
    user_permissions,
)

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_LIMIT_WINDOW_SECONDS = 300
LOGIN_LIMIT_MAX_ATTEMPTS = 5
_login_attempts: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _check_login_rate_limit(request: Request) -> None:
    now = monotonic()
    attempts = _login_attempts[_client_ip(request)]
    while attempts and now - attempts[0] > LOGIN_LIMIT_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= LOGIN_LIMIT_MAX_ATTEMPTS:
        raise BusinessException(TOO_MANY_REQUESTS, "Too many login attempts, please try again later")
    attempts.append(now)


def _role_out(role) -> RoleOut:
    return RoleOut(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        is_active=role.is_active,
        menu_ids=[menu.id for menu in role.menus],
        permission_ids=[permission.id for permission in role.permissions],
    )


@router.post("/login", response_model=ApiResponse[LoginResponse])
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> ApiResponse[LoginResponse]:
    _check_login_rate_limit(request)
    user = authenticate_user(db, payload.username, payload.password)
    _login_attempts.pop(_client_ip(request), None)
    return success(issue_login_response(user), msg="Login succeeded")


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> ApiResponse[TokenResponse]:
    return success(refresh_access_token(db, payload.refresh_token), msg="Refresh succeeded")


@router.post("/logout", response_model=ApiResponse[None])
def logout(payload: RefreshTokenRequest, request: Request) -> ApiResponse[None]:
    scheme, _, access_token = request.headers.get("Authorization", "").partition(" ")
    logout_token(payload.refresh_token, access_token if scheme.lower() == "bearer" else None)
    return success(msg="Logout succeeded")


@router.get("/me", response_model=ApiResponse[CurrentUserOut])
def current_user(user: User = Depends(get_current_user)) -> ApiResponse[CurrentUserOut]:
    permissions = user_permissions(user)
    return success(
        CurrentUserOut(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            department=user.department,
            roles=[_role_out(role) for role in user.roles],
            permissions=[PermissionOut.model_validate(permission) for permission in permissions],
            menus=build_menu_tree(user_menus(user)),
        )
    )


@router.patch("/me/password", response_model=ApiResponse[None])
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    db_user = db.get(User, user.id)
    if db_user is None:
        raise BusinessException(UNAUTHORIZED, "身份失效")
    if not verify_password(payload.old_password, db_user.hashed_password):
        raise BusinessException(BAD_REQUEST, "原密码不正确")
    if verify_password(payload.new_password, db_user.hashed_password):
        raise BusinessException(BAD_REQUEST, "新密码不能与原密码相同")
    db_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    scheme, _, access_token = request.headers.get("Authorization", "").partition(" ")
    logout_token(None, access_token if scheme.lower() == "bearer" else None)
    return success(msg="密码已修改，请重新登录")


@router.delete("/me", response_model=ApiResponse[None])
def cancel_account(
    payload: AccountCancelRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    db_user = db.get(User, user.id)
    if db_user is None:
        raise BusinessException(UNAUTHORIZED, "身份失效")
    if db_user.is_superuser:
        raise BusinessException(BAD_REQUEST, "超级管理员账号不允许注销")
    if not verify_password(payload.password, db_user.hashed_password):
        raise BusinessException(BAD_REQUEST, "密码不正确")
    scheme, _, access_token = request.headers.get("Authorization", "").partition(" ")
    logout_token(None, access_token if scheme.lower() == "bearer" else None)
    rbac_service.delete_user(db, db_user.id)
    return success(msg="账号已注销")
