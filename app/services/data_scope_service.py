from typing import Any

from sqlalchemy import or_

from app.models.rbac import User
from app.models.workover import WorkoverProjectPool

FULL_SCOPE_ROLES = {"super_admin", "ops_admin", "business_reviewer"}


def user_role_codes(user: User) -> set[str]:
    return {role.code for role in user.roles if role.is_active}


def can_view_all_data(user: User) -> bool:
    return user.is_superuser or bool(user_role_codes(user) & FULL_SCOPE_ROLES)


def project_pool_scope_predicate(user: User) -> dict[str, Any]:
    if can_view_all_data(user):
        return {"all": True}
    return {"created_by_id": user.id, "department": user.department}


def apply_project_pool_scope(stmt, user: User):
    scope = project_pool_scope_predicate(user)
    if scope.get("all"):
        return stmt

    clauses = [WorkoverProjectPool.created_by_id == scope["created_by_id"]]
    department = scope.get("department")
    if department:
        clauses.extend(
            [
                WorkoverProjectPool.report_unit == department,
                WorkoverProjectPool.territory_unit == department,
            ]
        )
    return stmt.where(or_(*clauses))
