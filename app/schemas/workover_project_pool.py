from datetime import datetime
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


class WorkoverProjectPoolBase(BaseModel):
    well_no: str = Field(min_length=1, max_length=64)
    well_name: str | None = Field(default=None, max_length=128)
    layer: str | None = Field(default=None, max_length=128)
    fault_description: str | None = None
    territory_unit: str | None = Field(default=None, max_length=128)
    block_name: str | None = Field(default=None, max_length=128)
    report_unit: str = Field(min_length=1, max_length=128)
    production_priority: int = Field(default=0, ge=0)
    reason: str | None = None
    measures_jsonb: MeasuresPayload = Field(default_factory=MeasuresPayload)
    remark: str | None = None


class WorkoverProjectPoolCreate(WorkoverProjectPoolBase):
    pass


class WorkoverProjectPoolUpdate(WorkoverProjectPoolBase):
    status: ProjectPoolStatus = ProjectPoolStatus.DRAFT


class WorkoverProjectPoolStatusPatch(BaseModel):
    status: ProjectPoolStatus
    comment: str | None = None


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


class WorkoverProjectPoolOut(BaseModel):
    id: int
    well_no: str
    well_name: str | None = None
    layer: str | None = None
    fault_description: str | None = None
    territory_unit: str | None = None
    block_name: str | None = None
    report_unit: str
    production_priority: int
    status: ProjectPoolStatus
    reason: str | None = None
    measures_jsonb: dict[str, Any]
    remark: str | None = None
    created_by_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImportTaskOut(BaseModel):
    task_id: str
    status: str
    imported_count: int = 0
    message: str | None = None
