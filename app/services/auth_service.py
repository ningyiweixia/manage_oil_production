from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessException
from app.core.security import verify_password
from app.core.status_codes import FORBIDDEN, UNAUTHORIZED
from app.models.rbac import Role, User


def authenticate_user(db: Session, username: str, password: str) -> User:
    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.username == username)
    )
    user = db.scalar(stmt)
    if not user or not verify_password(password, user.hashed_password):
        raise BusinessException(UNAUTHORIZED, "用户名或密码错误")
    if not user.is_active:
        raise BusinessException(FORBIDDEN, "账号已停用")
    return user


def get_user_permissions(user: User) -> set[str]:
    return {permission.code for role in user.roles for permission in role.permissions}
