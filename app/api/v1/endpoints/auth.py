from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.auth import CurrentUserOut, LoginRequest, LoginResponse, RefreshTokenRequest, TokenResponse
from app.schemas.response import ApiResponse, success
from app.services.auth_service import (
    authenticate_user,
    issue_login_response,
    logout_token,
    refresh_access_token,
    user_menus,
    user_permissions,
    build_menu_tree,
)
from app.schemas.rbac import PermissionOut, RoleOut

router = APIRouter(prefix="/auth", tags=["认证"])


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
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> ApiResponse[LoginResponse]:
    user = authenticate_user(db, payload.username, payload.password)
    return success(issue_login_response(user), msg="登录成功")


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> ApiResponse[TokenResponse]:
    return success(refresh_access_token(db, payload.refresh_token), msg="刷新成功")


@router.post("/logout", response_model=ApiResponse[None])
def logout(payload: RefreshTokenRequest, request: Request) -> ApiResponse[None]:
    scheme, _, access_token = request.headers.get("Authorization", "").partition(" ")
    logout_token(payload.refresh_token, access_token if scheme.lower() == "bearer" else None)
    return success(msg="登出成功")


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
