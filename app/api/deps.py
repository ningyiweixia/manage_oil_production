from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessException
from app.core.status_codes import FORBIDDEN, UNAUTHORIZED
from app.db.session import get_db
from app.models.rbac import Role, User
from app.services.auth_service import get_user_permissions


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise BusinessException(UNAUTHORIZED, "身份失效")

    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id, User.is_active.is_(True))
    )
    user = db.scalar(stmt)
    if user is None:
        raise BusinessException(UNAUTHORIZED, "身份失效")
    return user


def require_permission(permission_code: str) -> Callable[[User], User]:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        permissions = get_user_permissions(current_user)
        if permission_code not in permissions:
            raise BusinessException(FORBIDDEN, "越权访问")
        return current_user

    return dependency
