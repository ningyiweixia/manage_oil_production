from collections import defaultdict, deque
from time import monotonic

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import BusinessException
from app.core.status_codes import TOO_MANY_REQUESTS
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.auth import CurrentUserOut, LoginRequest, LoginResponse, RefreshTokenRequest, TokenResponse
from app.schemas.response import ApiResponse, success
from app.schemas.rbac import PermissionOut, RoleOut
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
