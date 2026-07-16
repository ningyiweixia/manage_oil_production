from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.workover import ProjectPoolStatus


class WorkoverMeasure(BaseModel):
    measure_type: str = Field(min_length=1, max_length=128)
    process: str | None = Field(default=None, max_length=128)
    construction_params: dict[str, Any] = Field(default_factory=dict)
    duration_days: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0)


class MeasuresPayload(BaseModel):
    measures: list[WorkoverMeasure] = Field(default_factory=list)

    @field_validator("measures")
    @classmethod
    def validate_unique_measure_type(cls, value: list[WorkoverMeasure]) -> list[WorkoverMeasure]:
        measure_types = [item.measure_type for item in value]
        if len(measure_types) != len(set(measure_types)):
            raise ValueError("measure_type must be unique inside measures_jsonb.measures")
        return value


class WorkoverAttachment(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1)
    content_type: str = Field(min_length=1, max_length=128)
    size: int = Field(ge=0)
    category: str = Field(min_length=1, max_length=64)
    uploaded_by: str | None = Field(default=None, max_length=64)
    uploaded_at: datetime | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if value.startswith(("http://", "https://", "data:image/", "/")):
            return value
        raise ValueError("attachment url must be http(s), data:image, or absolute storage path")

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, value: str) -> str:
        allowed = {
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/bmp",
            "application/pdf",
        }
        if value not in allowed:
            raise ValueError(f"content_type must be one of {sorted(allowed)}")
        return value


class WorkoverProjectPoolBase(BaseModel):
    well_no: str = Field(min_length=1, max_length=64)
    well_name: str | None = Field(default=None, max_length=128)
    well_type: str | None = Field(default=None, max_length=64)
    layer: str | None = Field(default=None, max_length=128)
    fault_description: str | None = None
    territory_unit: str | None = Field(default=None, max_length=128)
    block_name: str | None = Field(default=None, max_length=128)
    county: str | None = Field(default=None, max_length=64)
    report_unit: str = Field(min_length=1, max_length=128)
    initiator_name: str | None = Field(default=None, max_length=64)
    initiator_phone: str | None = Field(default=None, max_length=32)
    production_priority: int = Field(default=0, ge=0)
    reason: str | None = None
    reason_category: str | None = Field(default=None, max_length=64)
    completeness_status: str = Field(default="INCOMPLETE", max_length=32)
    data_source: str = Field(default="manual", max_length=32)
    report_batch: str | None = Field(default=None, max_length=64)
    photo_requirement: str | None = Field(default=None, max_length=255)
    rejection_supplement: str | None = None
    is_duplicate_well: bool = False
    related_project_ids: list[int] = Field(default_factory=list)
    measures_jsonb: MeasuresPayload = Field(default_factory=MeasuresPayload)
    photo_urls: list[str] = Field(default_factory=list)
    attachments: list[WorkoverAttachment] = Field(default_factory=list)
    remark: str | None = None

    @field_validator("initiator_phone")
    @classmethod
    def validate_initiator_phone(cls, value: str | None) -> str | None:
        if not value:
            return value
        normalized = value.strip()
        if not normalized.replace("-", "").replace(" ", "").isdigit() or len(normalized.replace("-", "").replace(" ", "")) < 7:
            raise ValueError("initiator_phone must be a valid phone number")
        return normalized

    @field_validator("completeness_status")
    @classmethod
    def validate_completeness_status(cls, value: str) -> str:
        allowed = {"INCOMPLETE", "COMPLETE", "NEEDS_SUPPLEMENT"}
        if value not in allowed:
            raise ValueError(f"completeness_status must be one of {sorted(allowed)}")
        return value

    @field_validator("data_source")
    @classmethod
    def validate_data_source(cls, value: str) -> str:
        allowed = {"manual", "excel", "external"}
        if value not in allowed:
            raise ValueError(f"data_source must be one of {sorted(allowed)}")
        return value


class WorkoverProjectPoolCreate(WorkoverProjectPoolBase):
    pass


class WorkoverProjectPoolUpdate(WorkoverProjectPoolBase):
    pass


class WorkoverProjectPoolStatusPatch(BaseModel):
    status: ProjectPoolStatus
    comment: str | None = None
    geology_verified_daily_oil: Decimal | None = Field(default=None, ge=0)
    process_well_condition: str | None = None
    process_can_workover: bool | None = None


class WorkoverProjectPoolSubmit(BaseModel):
    project_ids: list[int] = Field(min_length=1)
    comment: str | None = None


class WorkoverProjectPoolQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    block_name: str | None = None
    well_no: str | None = None
    status: ProjectPoolStatus | None = None
    measure_type: str | None = None
    report_unit: str | None = None


class WorkoverAnalyticsQuery(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    block_name: str | None = None
    status: ProjectPoolStatus | None = None
    measure_type: str | None = None
    report_unit: str | None = None


class AnalyticsKpiOut(BaseModel):
    total_projects: int = 0
    pending_approvals: int = 0
    approval_rate: float = 0
    estimated_cost: float = 0
    average_priority: float = 0


class NameValueOut(BaseModel):
    name: str
    value: float


class StatusCountOut(BaseModel):
    status: ProjectPoolStatus
    label: str
    count: int


class HeatmapOut(BaseModel):
    blocks: list[str]
    statuses: list[ProjectPoolStatus]
    data: list[tuple[int, int, float]]


class TrendOut(BaseModel):
    days: list[str]
    counts: list[int]
    costs: list[float]


class WorkoverAnalyticsOut(BaseModel):
    kpis: AnalyticsKpiOut
    status_counts: list[StatusCountOut]
    measure_distribution: list[NameValueOut]
    heatmap: HeatmapOut
    trend: TrendOut
    measure_types: list[str]


class WorkoverProjectPoolOut(BaseModel):
    id: int
    well_no: str
    well_name: str | None = None
    well_type: str | None = None
    layer: str | None = None
    fault_description: str | None = None
    territory_unit: str | None = None
    block_name: str | None = None
    county: str | None = None
    report_unit: str
    initiator_name: str | None = None
    initiator_phone: str | None = None
    production_priority: int
    geology_verified_daily_oil: Decimal | None = None
    geology_verified_at: datetime | None = None
    process_well_condition: str | None = None
    process_can_workover: bool | None = None
    process_verified_at: datetime | None = None
    status: ProjectPoolStatus
    reason: str | None = None
    reason_category: str | None = None
    completeness_status: str = "INCOMPLETE"
    data_source: str = "manual"
    report_batch: str | None = None
    photo_requirement: str | None = None
    rejection_supplement: str | None = None
    is_duplicate_well: bool = False
    related_project_ids: list[int] = []
    measures_jsonb: dict[str, Any]
    photo_urls: list[str] = []
    attachments: list[WorkoverAttachment] = []
    remark: str | None = None
    created_by_id: int | None = None
    created_at: datetime
    updated_at: datetime
    rejected_from_status: ProjectPoolStatus | None = None

    model_config = ConfigDict(from_attributes=True)


class ImportTaskOut(BaseModel):
    task_id: str
    status: str
    imported_count: int = 0
    message: str | None = None
    errors: list[str] = Field(default_factory=list)
