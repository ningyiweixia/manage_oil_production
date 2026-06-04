from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.crud.rbac import list_operation_logs
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.rbac import (
    IdsPayload,
    MenuCreate,
    MenuOut,
    MenuUpdate,
    OperationLogOut,
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
from app.schemas.response import ApiResponse, success
from app.services import rbac_service

router = APIRouter(tags=["系统管理"])


@router.get("/users", response_model=ApiResponse[list[UserOut]])
def users(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:user:read")),
) -> ApiResponse[list[UserOut]]:
    return success(rbac_service.list_users(db))


@router.post("/users", response_model=ApiResponse[UserOut])
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:user:create")),
) -> ApiResponse[UserOut]:
    return success(rbac_service.create_user(db, payload), msg="创建成功")


@router.put("/users/{user_id}", response_model=ApiResponse[UserOut])
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:user:update")),
) -> ApiResponse[UserOut]:
    return success(rbac_service.update_user(db, user_id, payload), msg="更新成功")


@router.patch("/users/{user_id}/active", response_model=ApiResponse[UserOut])
def set_user_active(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:user:update")),
) -> ApiResponse[UserOut]:
    return success(rbac_service.set_user_active(db, user_id, is_active), msg="状态已更新")


@router.patch("/users/{user_id}/roles", response_model=ApiResponse[UserOut])
def assign_user_roles(
    user_id: int,
    payload: IdsPayload,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:user:assign_roles")),
) -> ApiResponse[UserOut]:
    return success(rbac_service.assign_user_roles(db, user_id, payload.ids), msg="角色已分配")


@router.delete("/users/{user_id}", response_model=ApiResponse[None])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:user:delete")),
) -> ApiResponse[None]:
    rbac_service.delete_user(db, user_id)
    return success(msg="已停用")


@router.get("/roles", response_model=ApiResponse[list[RoleOut]])
def roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:role:read")),
) -> ApiResponse[list[RoleOut]]:
    return success(rbac_service.list_roles(db))


@router.post("/roles", response_model=ApiResponse[RoleOut])
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:role:create")),
) -> ApiResponse[RoleOut]:
    return success(rbac_service.create_role(db, payload), msg="创建成功")


@router.put("/roles/{role_id}", response_model=ApiResponse[RoleOut])
def update_role(
    role_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:role:update")),
) -> ApiResponse[RoleOut]:
    return success(rbac_service.update_role(db, role_id, payload), msg="更新成功")


@router.patch("/roles/{role_id}/menus", response_model=ApiResponse[RoleOut])
def assign_role_menus(
    role_id: int,
    payload: IdsPayload,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:role:assign_menus")),
) -> ApiResponse[RoleOut]:
    return success(rbac_service.assign_role_menus(db, role_id, payload.ids), msg="菜单已分配")


@router.patch("/roles/{role_id}/permissions", response_model=ApiResponse[RoleOut])
def assign_role_permissions(
    role_id: int,
    payload: IdsPayload,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:role:assign_permissions")),
) -> ApiResponse[RoleOut]:
    return success(rbac_service.assign_role_permissions(db, role_id, payload.ids), msg="权限已绑定")


@router.delete("/roles/{role_id}", response_model=ApiResponse[None])
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:role:delete")),
) -> ApiResponse[None]:
    rbac_service.delete_role(db, role_id)
    return success(msg="已删除")


@router.get("/menus", response_model=ApiResponse[list[MenuOut]])
def menus(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:menu:read")),
) -> ApiResponse[list[MenuOut]]:
    return success(rbac_service.list_menu_tree(db))


@router.post("/menus", response_model=ApiResponse[MenuOut])
def create_menu(
    payload: MenuCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:menu:create")),
) -> ApiResponse[MenuOut]:
    return success(rbac_service.create_menu(db, payload), msg="创建成功")


@router.put("/menus/{menu_id}", response_model=ApiResponse[MenuOut])
def update_menu(
    menu_id: int,
    payload: MenuUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:menu:update")),
) -> ApiResponse[MenuOut]:
    return success(rbac_service.update_menu(db, menu_id, payload), msg="更新成功")


@router.delete("/menus/{menu_id}", response_model=ApiResponse[None])
def delete_menu(
    menu_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:menu:delete")),
) -> ApiResponse[None]:
    rbac_service.delete_menu(db, menu_id)
    return success(msg="已删除")


@router.get("/permissions", response_model=ApiResponse[list[PermissionOut]])
def permissions(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:permission:read")),
) -> ApiResponse[list[PermissionOut]]:
    return success(rbac_service.list_permissions(db))


@router.post("/permissions", response_model=ApiResponse[PermissionOut])
def create_permission(
    payload: PermissionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:permission:create")),
) -> ApiResponse[PermissionOut]:
    return success(rbac_service.create_permission(db, payload), msg="创建成功")


@router.put("/permissions/{permission_id}", response_model=ApiResponse[PermissionOut])
def update_permission(
    permission_id: int,
    payload: PermissionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:permission:update")),
) -> ApiResponse[PermissionOut]:
    return success(rbac_service.update_permission(db, permission_id, payload), msg="更新成功")


@router.delete("/permissions/{permission_id}", response_model=ApiResponse[None])
def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:permission:delete")),
) -> ApiResponse[None]:
    rbac_service.delete_permission(db, permission_id)
    return success(msg="已删除")


@router.get("/operation-logs", response_model=ApiResponse[list[OperationLogOut]])
def operation_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("system:operation_log:read")),
) -> ApiResponse[list[OperationLogOut]]:
    return success([OperationLogOut.model_validate(row) for row in list_operation_logs(db)])
