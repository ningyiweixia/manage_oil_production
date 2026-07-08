from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.approval_workflow import (
    ApprovalDecision,
    ApprovalTaskOut,
    ApprovalTaskQuery,
    ApprovalTimelineItemOut,
)
from app.schemas.pagination import PageResult
from app.schemas.response import ApiResponse, success
from app.schemas.workover_project_pool import WorkoverProjectPoolOut
from app.services.approval_workflow_service import (
    get_approval_timeline,
    list_approval_tasks,
    process_workover_project_approval,
)
from app.services.notification_service import push_status_changed

router = APIRouter(tags=["审核审批"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/approvals/tasks", response_model=ApiResponse[PageResult[ApprovalTaskOut]])
def approval_tasks(
    query: ApprovalTaskQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("approval:task:read")),
) -> ApiResponse[PageResult[ApprovalTaskOut]]:
    return success(list_approval_tasks(db, query, current_user))


@router.get("/approvals/{business_type}/{business_id}/timeline", response_model=ApiResponse[list[ApprovalTimelineItemOut]])
def approval_timeline(
    business_type: str,
    business_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("approval:timeline:read")),
) -> ApiResponse[list[ApprovalTimelineItemOut]]:
    return success(get_approval_timeline(db, business_type, business_id))


@router.patch("/approvals/workover-project-pools/{project_id}", response_model=ApiResponse[WorkoverProjectPoolOut])
async def process_project_pool_approval(
    project_id: int,
    decision: ApprovalDecision,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("approval:process")),
) -> ApiResponse[WorkoverProjectPoolOut]:
    project = process_workover_project_approval(
        db,
        project_id,
        decision,
        operator_id=current_user.id,
        operator_ip=_client_ip(request),
        current_user=current_user,
        geology_verified_daily_oil=decision.geology_verified_daily_oil,
        process_well_condition=decision.process_well_condition,
        process_can_workover=decision.process_can_workover,
    )
    await push_status_changed(
        {
            "node_code": project.status.value,
            "project_id": project.id,
            "well_no": project.well_no,
        }
    )
    return success(WorkoverProjectPoolOut.model_validate(project), msg="审批处理成功")
