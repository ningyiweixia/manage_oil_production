from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.workover import (
    ContractorCapacitySourceType,
    ContractorCapacityStatus,
    ContractorCapacitySyncResultStatus,
    ContractorCapacitySyncStatus,
    ContractorCapacitySyncType,
    OperationStatus,
)


class ContractorCapacityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contractor_name: str = Field(min_length=1, max_length=128)
    team_name: str = Field(min_length=1, max_length=128)
    report_date: date
    available_count: int = Field(default=0, ge=0)
    status: ContractorCapacityStatus = ContractorCapacityStatus.AVAILABLE
    capability_tags: dict[str, Any] = Field(min_length=1)
    sync_error_message: str | None = Field(default=None, max_length=500)
    contact_name: str | None = Field(default=None, max_length=64)
    contact_phone: str | None = Field(default=None, max_length=32)
    qualification_expire_at: date | None = None
    equipment_summary: str | None = None

    @field_validator("capability_tags")
    @classmethod
    def validate_capability_tags(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not any(item is True or item == "true" or item == 1 for item in value.values()):
            raise ValueError("capability_tags must include at least one enabled capability")
        return value


class ContractorCapacityUpdate(BaseModel):
    """人工维护基础资料。

    运力数量、队伍状态、来源类型和同步状态由补录、同步确认、异常处理、派工/释放等专门流程维护。
    """

    contractor_name: str | None = Field(default=None, min_length=1, max_length=128)
    team_name: str | None = Field(default=None, min_length=1, max_length=128)
    report_date: date | None = None
    capability_tags: dict[str, Any] | None = None
    external_status: str | None = Field(default=None, max_length=64)
    sync_error_message: str | None = None
    contact_name: str | None = Field(default=None, max_length=64)
    contact_phone: str | None = Field(default=None, max_length=32)
    qualification_expire_at: date | None = None
    equipment_summary: str | None = None

    @field_validator("capability_tags")
    @classmethod
    def validate_optional_capability_tags(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None and not any(item is True or item == "true" or item == 1 for item in value.values()):
            raise ValueError("capability_tags must include at least one enabled capability")
        return value


class ContractorCapacityQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    contractor_name: str | None = None
    team_name: str | None = None
    report_date: date | None = None
    status: ContractorCapacityStatus | None = None
    capability_tag: str | None = None
    source_type: ContractorCapacitySourceType | None = None
    sync_status: ContractorCapacitySyncStatus | None = None


class ContractorCapacityOut(BaseModel):
    id: int
    contractor_name: str
    team_name: str
    report_date: date
    available_count: int
    status: ContractorCapacityStatus
    capability_tags: dict[str, Any]
    external_system_id: str | None = None
    external_status: str | None = None
    source_type: ContractorCapacitySourceType
    sync_status: ContractorCapacitySyncStatus
    last_synced_at: datetime | None = None
    sync_error_message: str | None = None
    confirmed_at: datetime | None = None
    confirmed_by_id: int | None = None
    created_by_id: int | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    qualification_expire_at: date | None = None
    equipment_summary: str | None = None
    occupied_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContractorSyncPayload(BaseModel):
    report_date: date | None = None


class ContractorExceptionPayload(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ContractorCapacitySyncLogQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    status: ContractorCapacitySyncResultStatus | None = None
    sync_type: ContractorCapacitySyncType | None = None


class ContractorCapacitySyncLogOut(BaseModel):
    id: int
    sync_type: ContractorCapacitySyncType
    status: ContractorCapacitySyncResultStatus
    started_at: datetime
    finished_at: datetime | None = None
    success_count: int
    failed_count: int
    created_count: int
    updated_count: int
    ignored_count: int
    error_message: str | None = None
    operator_id: int | None = None
    raw_summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContractorSyncSummary(BaseModel):
    connection_status: str
    last_sync_time: datetime | None = None
    last_sync_status: ContractorCapacitySyncResultStatus | None = None
    created_count: int = 0
    updated_count: int = 0
    ignored_count: int = 0
    failed_count: int = 0
    exception_count: int = 0


class ContractorCapacityOverview(BaseModel):
    reported_team_count: int
    available_team_count: int
    busy_team_count: int
    offline_team_count: int
    sync_exception_count: int
    major_repair_team_count: int


class ContractorOperationSheetLinkOut(BaseModel):
    id: int
    operation_no: str
    status: OperationStatus
    well_no: str | None = None
    dispatch_time: datetime | None = None
    a5_status: str | None = None
    created_at: datetime


class WorkoverOperationSheetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int = Field(ge=1)
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
    well_no: str | None = None
    block_name: str | None = None
    contractor_keyword: str | None = None
    start_date: date | None = None
    end_date: date | None = None


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
    last_a5_report_date: date | None = None
    a5_sync_result: str | None = None
    a5_sync_error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DispatchPayload(BaseModel):
    operation_sheet_id: int = Field(ge=1)
    contractor_capacity_id: int = Field(ge=1)
    redirect_path: str = Field(default="/measure-review", min_length=1, max_length=128)


class DispatchA5Out(BaseModel):
    sheet: WorkoverOperationSheetOut
    redirect_url: str
    token: str
    expire_at: datetime


class ProgressPatch(BaseModel):
    progress: int = Field(ge=0, le=100)
    progress_detail: dict[str, Any] = Field(default_factory=dict)
