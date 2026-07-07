from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.workover import ContractorCapacityStatus, OperationStatus


class ContractorCapacityCreate(BaseModel):
    contractor_name: str = Field(min_length=1, max_length=128)
    team_name: str = Field(min_length=1, max_length=128)
    report_date: date
    available_count: int = Field(default=0, ge=0)
    status: ContractorCapacityStatus = ContractorCapacityStatus.AVAILABLE
    capability_tags: dict[str, Any] = Field(default_factory=dict)


class ContractorCapacityUpdate(BaseModel):
    contractor_name: str | None = Field(default=None, min_length=1, max_length=128)
    team_name: str | None = Field(default=None, min_length=1, max_length=128)
    report_date: date | None = None
    available_count: int | None = Field(default=None, ge=0)
    status: ContractorCapacityStatus | None = None
    capability_tags: dict[str, Any] | None = None


class ContractorCapacityQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    contractor_name: str | None = None
    report_date: date | None = None
    status: ContractorCapacityStatus | None = None


class ContractorCapacityOut(BaseModel):
    id: int
    contractor_name: str
    team_name: str
    report_date: date
    available_count: int
    status: ContractorCapacityStatus
    capability_tags: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkoverOperationSheetCreate(BaseModel):
    project_id: int = Field(ge=1)
    contractor_capacity_id: int | None = None
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None


class WorkoverOperationSheetUpdate(BaseModel):
    contractor_capacity_id: int | None = None
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    progress_detail: dict[str, Any] | None = None


class WorkoverOperationSheetQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    status: OperationStatus | None = None
    project_id: int | None = None
    contractor_capacity_id: int | None = None


class WorkoverOperationSheetOut(BaseModel):
    id: int
    project_id: int
    project_well_no: str | None = None
    contractor_capacity_id: int | None = None
    operation_no: str
    status: OperationStatus
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None
    progress: int
    progress_detail: dict[str, Any]
    a5_status: str | None = None
    a5_remark: str | None = None
    last_a5_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DispatchPayload(BaseModel):
    operation_sheet_id: int = Field(ge=1)
    contractor_capacity_id: int = Field(ge=1)


class ProgressPatch(BaseModel):
    progress: int = Field(ge=0, le=100)
    progress_detail: dict[str, Any] = Field(default_factory=dict)
