from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST, CONFLICT, FORBIDDEN
from app.crud.workover_project_pool import (
    BUSINESS_TYPE,
    _batch_find_pre_rejection_status,
    get_project_pool,
    patch_project_status,
)
from app.models.approval import ApprovalAction, ApprovalLog
from app.models.rbac import User
from app.models.workover import ProjectPoolStatus, WorkoverProjectPool
from app.schemas.approval_workflow import (
    ApprovalActionCode,
    ApprovalDecision,
    ApprovalTaskOut,
    ApprovalTaskQuery,
    ApprovalTaskScope,
    ApprovalTimelineItemOut,
)
from app.schemas.pagination import PageResult
from app.schemas.workover_project_pool import WorkoverProjectPoolOut


@dataclass(frozen=True)
class ApprovalNodeRule:
    code: ProjectPoolStatus
    name: str
    allowed_roles: set[str]
    allowed_actions: tuple[ApprovalActionCode, ...]
    next_status: ProjectPoolStatus | None
    requirement: str

    @property
    def role_codes(self) -> set[str]:
        return self.allowed_roles


APPROVAL_NODE_RULES: dict[ProjectPoolStatus, ApprovalNodeRule] = {
    ProjectPoolStatus.PENDING_GEOLOGY_VERIFY: ApprovalNodeRule(
        code=ProjectPoolStatus.PENDING_GEOLOGY_VERIFY,
        name="地质核实",
        allowed_roles={"geology_reviewer", "production_command_reviewer", "business_reviewer"},
        allowed_actions=(ApprovalActionCode.APPROVE, ApprovalActionCode.REJECT),
        next_status=ProjectPoolStatus.PENDING_PROCESS_VERIFY,
        requirement="核实产量、油藏、层位和上修必要性。",
    ),
    ProjectPoolStatus.PENDING_PROCESS_VERIFY: ApprovalNodeRule(
        code=ProjectPoolStatus.PENDING_PROCESS_VERIFY,
        name="工艺核实",
        allowed_roles={"process_reviewer", "business_reviewer"},
        allowed_actions=(ApprovalActionCode.APPROVE, ApprovalActionCode.REJECT),
        next_status=ProjectPoolStatus.APPROVED,
        requirement="核实井况、措施参数、施工可行性和入运行库条件。",
    ),
}

ACTION_LABELS = {
    ApprovalAction.CREATE: "创建",
    ApprovalAction.UPDATE: "更新",
    ApprovalAction.DELETE: "删除",
    ApprovalAction.VOID: "作废",
    ApprovalAction.SUBMIT: "提交",
    ApprovalAction.APPROVE: "通过",
    ApprovalAction.REJECT: "驳回",
    ApprovalAction.ROLLBACK: "退回",
}


def _role_codes(user: User) -> set[str]:
    return {role.code for role in getattr(user, "roles", []) if getattr(role, "is_active", True)}


def _is_superuser(user: User) -> bool:
    return bool(getattr(user, "is_superuser", False))


def ensure_node_actor_allowed(user: User, node_status: ProjectPoolStatus) -> None:
    rule = APPROVAL_NODE_RULES.get(node_status)
    if rule is None:
        raise BusinessException(CONFLICT, "当前状态不属于审批节点")
    if _is_superuser(user):
        return
    if _role_codes(user).isdisjoint(rule.allowed_roles):
        raise BusinessException(FORBIDDEN, f"当前用户无权处理{rule.name}")


def validate_approval_decision(decision: ApprovalDecision) -> None:
    if decision.action == ApprovalActionCode.REJECT and not (decision.comment or "").strip():
        raise BusinessException(BAD_REQUEST, "驳回时必须填写原因")


def _measure_summary(project: WorkoverProjectPool) -> str | None:
    measures = (project.measures_jsonb or {}).get("measures", [])
    if not isinstance(measures, list):
        return None
    parts = []
    for item in measures:
        if isinstance(item, dict):
            measure_type = item.get("measure_type")
            process = item.get("process")
            parts.append(" / ".join(str(value) for value in [measure_type, process] if value))
    return "；".join(parts) or None


def _stay_hours(project: WorkoverProjectPool) -> float:
    base = project.updated_at or project.created_at
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return round(max((datetime.now(timezone.utc) - base).total_seconds(), 0) / 3600, 1)


def _last_comment(db: Session, project_id: int) -> str | None:
    log = db.scalar(
        select(ApprovalLog)
        .where(ApprovalLog.business_type == BUSINESS_TYPE, ApprovalLog.business_id == project_id)
        .order_by(desc(ApprovalLog.created_at))
        .limit(1)
    )
    return log.comment if log else None


def _task_from_project(db: Session, project: WorkoverProjectPool, user: User) -> ApprovalTaskOut:
    rejected_from = None
    if project.status == ProjectPoolStatus.REJECTED:
        rejected_from = _batch_find_pre_rejection_status(db, [project.id]).get(project.id)
    out = WorkoverProjectPoolOut.model_validate(project)
    out.rejected_from_status = rejected_from

    node_status = rejected_from if project.status == ProjectPoolStatus.REJECTED and rejected_from else project.status
    rule = APPROVAL_NODE_RULES.get(node_status)
    can_process = bool(rule and (_is_superuser(user) or not _role_codes(user).isdisjoint(rule.allowed_roles)))
    allowed_actions = list(rule.allowed_actions) if rule and project.status != ProjectPoolStatus.REJECTED else [ApprovalActionCode.RESUBMIT]
    if project.status == ProjectPoolStatus.APPROVED:
        node_label = "已通过，进入运行库"
    elif project.status == ProjectPoolStatus.REJECTED:
        node_label = f"{rule.name if rule else '审批'}驳回"
    else:
        node_label = rule.name if rule else project.status.value

    return ApprovalTaskOut(
        business_id=project.id,
        project=out,
        current_node=node_status.value if isinstance(node_status, ProjectPoolStatus) else str(node_status),
        node_label=node_label,
        allowed_actions=allowed_actions,
        can_process=can_process,
        stay_hours=_stay_hours(project),
        measure_summary=_measure_summary(project),
        last_comment=_last_comment(db, project.id),
    )


def _pending_statuses_for_user(user: User) -> list[ProjectPoolStatus]:
    if _is_superuser(user):
        return list(APPROVAL_NODE_RULES)
    roles = _role_codes(user)
    return [status for status, rule in APPROVAL_NODE_RULES.items() if not roles.isdisjoint(rule.allowed_roles)]


def list_approval_tasks(db: Session, query: ApprovalTaskQuery, user: User) -> PageResult[ApprovalTaskOut]:
    stmt = select(WorkoverProjectPool).where(WorkoverProjectPool.is_deleted.is_(False))
    if query.well_no:
        stmt = stmt.where(WorkoverProjectPool.well_no.ilike(f"%{query.well_no}%"))

    if query.scope == ApprovalTaskScope.PENDING:
        statuses = _pending_statuses_for_user(user)
        if not statuses:
            return PageResult(items=[], total=0, page=query.page, page_size=query.page_size)
        stmt = stmt.where(WorkoverProjectPool.status.in_(statuses))
    elif query.scope == ApprovalTaskScope.REJECTED:
        stmt = stmt.where(WorkoverProjectPool.status == ProjectPoolStatus.REJECTED)
    elif query.scope == ApprovalTaskScope.APPROVED:
        stmt = stmt.where(WorkoverProjectPool.status.in_([ProjectPoolStatus.APPROVED, ProjectPoolStatus.DISPATCHED]))
    else:
        handled_ids = select(ApprovalLog.business_id).where(
            ApprovalLog.business_type == BUSINESS_TYPE,
            ApprovalLog.operator_id == user.id,
            ApprovalLog.action.in_([ApprovalAction.APPROVE, ApprovalAction.REJECT, ApprovalAction.SUBMIT]),
        )
        stmt = stmt.where(WorkoverProjectPool.id.in_(handled_ids))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(WorkoverProjectPool.updated_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return PageResult(
        items=[_task_from_project(db, project, user) for project in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


def get_approval_timeline(db: Session, business_type: str, business_id: int) -> list[ApprovalTimelineItemOut]:
    rows = db.scalars(
        select(ApprovalLog)
        .where(ApprovalLog.business_type == business_type, ApprovalLog.business_id == business_id)
        .order_by(ApprovalLog.created_at.asc(), ApprovalLog.id.asc())
    ).all()
    result: list[ApprovalTimelineItemOut] = []
    for row in rows:
        before_status = (row.before_snapshot or {}).get("status")
        after_status = (row.after_snapshot or {}).get("status")
        node_status = None
        try:
            node_status = ProjectPoolStatus(row.node_code)
        except ValueError:
            pass
        node_label = APPROVAL_NODE_RULES[node_status].name if node_status in APPROVAL_NODE_RULES else row.node_code
        result.append(
            ApprovalTimelineItemOut(
                id=row.id,
                business_type=row.business_type,
                business_id=row.business_id,
                node_code=row.node_code,
                node_label=node_label,
                action=row.action.value,
                action_label=ACTION_LABELS.get(row.action, row.action.value),
                comment=row.comment,
                operator_id=row.operator_id,
                operator_name=row.operator.full_name if row.operator else None,
                before_status=before_status,
                after_status=after_status,
                created_at=row.created_at,
            )
        )
    return result


def process_workover_project_approval(
    db: Session,
    project_id: int,
    decision: ApprovalDecision,
    *,
    operator_id: int,
    operator_ip: str | None,
    current_user: User,
    geology_verified_daily_oil=None,
    process_well_condition: str | None = None,
    process_can_workover: bool | None = None,
) -> WorkoverProjectPool:
    validate_approval_decision(decision)
    project = get_project_pool(db, project_id)

    if decision.action == ApprovalActionCode.RESUBMIT:
        if project.status != ProjectPoolStatus.REJECTED:
            raise BusinessException(CONFLICT, "只有已驳回项目可以重新提报")
        return patch_project_status(
            db,
            project_id,
            ProjectPoolStatus.PENDING_GEOLOGY_VERIFY,
            operator_id=operator_id,
            operator_ip=operator_ip,
            comment=decision.comment or "重新提报",
        )

    ensure_node_actor_allowed(current_user, project.status)
    rule = APPROVAL_NODE_RULES[project.status]
    target_status = ProjectPoolStatus.REJECTED if decision.action == ApprovalActionCode.REJECT else rule.next_status
    if target_status is None:
        raise BusinessException(CONFLICT, "当前节点缺少下一节点配置")
    return patch_project_status(
        db,
        project_id,
        target_status,
        operator_id=operator_id,
        operator_ip=operator_ip,
        comment=decision.comment,
        geology_verified_daily_oil=geology_verified_daily_oil,
        process_well_condition=process_well_condition,
        process_can_workover=process_can_workover,
    )
