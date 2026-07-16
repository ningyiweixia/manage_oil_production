from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, true

from app.models.rbac import User
from app.models.workover import ContractorCapacity, WorkoverProjectPool

FULL_SCOPE_ROLES = {"super_admin", "ops_admin", "business_reviewer", "process_reviewer", "project_pool_admin"}


class DataScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_global: bool
    user_id: int
    department: str | None = None
    reporting_units: tuple[str, ...] = ()


def user_role_codes(user: User) -> set[str]:
    return {role.code for role in getattr(user, "roles", []) if getattr(role, "is_active", True)}


def can_view_all_data(user: User) -> bool:
    return bool(getattr(user, "is_superuser", False)) or bool(user_role_codes(user) & FULL_SCOPE_ROLES)


def build_data_scope(user: User) -> DataScope:
    department = (user.department or "").strip() or None
    return DataScope(
        is_global=can_view_all_data(user),
        user_id=user.id,
        department=department,
        reporting_units=(department,) if department else (),
    )


def reporting_unit_scope_predicate(scope: DataScope):
    if scope.is_global:
        return true()
    if not scope.reporting_units:
        return WorkoverProjectPool.id.is_(None)
    return or_(
        WorkoverProjectPool.report_unit.in_(scope.reporting_units),
        WorkoverProjectPool.territory_unit.in_(scope.reporting_units),
    )


def project_pool_scope_predicate(user: User) -> dict[str, Any]:
    if can_view_all_data(user):
        return {"all": True}
    return {"created_by_id": user.id, "department": getattr(user, "department", None)}


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


def apply_workover_operation_scope(stmt, user: User):
    """Apply the project ownership/unit boundary to operation-sheet queries."""
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


def apply_contractor_capacity_read_scope(stmt, user: User):
    if can_view_all_data(user):
        return stmt
    return stmt.where(ContractorCapacity.created_by_id == user.id)


def can_manage_contractor_capacity(user: User, capacity: ContractorCapacity) -> bool:
    if can_view_all_data(user):
        return True
    return capacity.created_by_id == user.id
