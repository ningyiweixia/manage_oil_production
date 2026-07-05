from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.rbac import Menu, OperationLog, Permission, Role, User


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions), selectinload(User.roles).selectinload(Role.menus))
        .where(User.username == username)
    )


def get_user(db: Session, user_id: int) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions), selectinload(User.roles).selectinload(Role.menus))
        .where(User.id == user_id)
    )


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).options(selectinload(User.roles)).order_by(User.id.desc())).all())


def list_roles_by_ids(db: Session, role_ids: Sequence[int]) -> list[Role]:
    if not role_ids:
        return []
    return list(db.scalars(select(Role).where(Role.id.in_(role_ids))).all())


def list_menus_by_ids(db: Session, menu_ids: Sequence[int]) -> list[Menu]:
    if not menu_ids:
        return []
    return list(db.scalars(select(Menu).where(Menu.id.in_(menu_ids))).all())


def list_permissions_by_ids(db: Session, permission_ids: Sequence[int]) -> list[Permission]:
    if not permission_ids:
        return []
    return list(db.scalars(select(Permission).where(Permission.id.in_(permission_ids))).all())


def list_roles(db: Session) -> list[Role]:
    return list(db.scalars(select(Role).options(selectinload(Role.menus), selectinload(Role.permissions)).order_by(Role.id.desc())).all())


def list_menus(db: Session) -> list[Menu]:
    return list(db.scalars(select(Menu).order_by(Menu.sort_order.asc(), Menu.id.asc())).all())


def list_permissions(db: Session) -> list[Permission]:
    return list(db.scalars(select(Permission).order_by(Permission.id.desc())).all())


def list_operation_logs(db: Session, limit: int = 100) -> list[OperationLog]:
    return list(db.scalars(select(OperationLog).order_by(OperationLog.id.desc()).limit(limit)).all())


def paginate_operation_logs(db: Session, page: int = 1, page_size: int = 20) -> tuple[list[OperationLog], int]:
    total = db.scalar(select(func.count()).select_from(select(OperationLog).subquery())) or 0
    rows = db.scalars(
        select(OperationLog)
        .order_by(OperationLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total
