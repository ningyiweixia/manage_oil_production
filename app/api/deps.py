from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import FORBIDDEN, UNAUTHORIZED
from app.crud.rbac import get_user
from app.db.session import get_db
from app.models.rbac import User
from app.services.auth_service import get_user_permission_codes


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise BusinessException(UNAUTHORIZED, "身份失效")
    user = get_user(db, int(user_id))
    if user is None or not user.is_active:
        raise BusinessException(UNAUTHORIZED, "身份失效")
    return user


def require_permission(permission_code: str) -> Callable[[Request, Session, User], User]:
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        request.state.permission_code = permission_code
        permissions = get_user_permission_codes(db, current_user.id)
        if "*" not in permissions and permission_code not in permissions:
            raise BusinessException(FORBIDDEN, "越权访问")
        return current_user

    return dependency
