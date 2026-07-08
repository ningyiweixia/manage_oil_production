from datetime import datetime
from enum import Enum

from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.workover import ProjectPoolStatus
from app.schemas.workover_project_pool import WorkoverProjectPoolOut


class ApprovalActionCode(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RESUBMIT = "RESUBMIT"


class ApprovalTaskScope(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    REJECTED = "rejected"
    APPROVED = "approved"


class ApprovalDecision(BaseModel):
    action: ApprovalActionCode
    comment: str | None = Field(default=None, max_length=1000)
    geology_verified_daily_oil: Decimal | None = Field(default=None, ge=0)
    process_well_condition: str | None = Field(default=None, max_length=1000)
    process_can_workover: bool | None = None


class ApprovalTaskQuery(BaseModel):
    scope: ApprovalTaskScope = ApprovalTaskScope.PENDING
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    well_no: str | None = None


class ApprovalTaskOut(BaseModel):
    business_type: str = "workover_project_pool"
    business_id: int
    project: WorkoverProjectPoolOut
    current_node: str
    node_label: str
    allowed_actions: list[ApprovalActionCode]
    can_process: bool
    stay_hours: float
    measure_summary: str | None = None
    last_comment: str | None = None


class ApprovalTimelineItemOut(BaseModel):
    id: int
    business_type: str
    business_id: int
    node_code: str
    node_label: str
    action: str
    action_label: str
    comment: str | None = None
    operator_id: int | None = None
    operator_name: str | None = None
    before_status: str | None = None
    after_status: str | None = None
    created_at: datetime
