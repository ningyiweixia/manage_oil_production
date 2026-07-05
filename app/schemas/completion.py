from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WellCompletionCreate(BaseModel):
    well_no: str = Field(min_length=1, max_length=64)
    operation_sheet_id: int | None = None
    measure_type: str = Field(min_length=1, max_length=64)
    completion_date: date | None = None
    team_name: str | None = Field(default=None, max_length=128)
    pre_repair_data: dict[str, Any] = Field(default_factory=lambda: {"production_before": "", "pressure_before": "", "pump_efficiency_before": ""})
    post_repair_data: dict[str, Any] = Field(default_factory=lambda: {"production_after": "", "pressure_after": "", "pump_efficiency_after": ""})
    remark: str | None = None


class WellCompletionUpdate(BaseModel):
    well_no: str | None = Field(default=None, min_length=1, max_length=64)
    measure_type: str | None = Field(default=None, min_length=1, max_length=64)
    completion_date: date | None = None
    team_name: str | None = Field(default=None, max_length=128)
    pre_repair_data: dict[str, Any] | None = None
    post_repair_data: dict[str, Any] | None = None
    remark: str | None = None


class WellCompletionQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    well_no: str | None = None
    measure_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class WellCompletionOut(BaseModel):
    id: int
    well_no: str
    operation_sheet_id: int | None = None
    measure_type: str
    completion_date: date | None = None
    team_name: str | None = None
    pre_repair_data: dict[str, Any]
    post_repair_data: dict[str, Any]
    remark: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
