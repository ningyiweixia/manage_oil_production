from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.material import MaterialRequirementStatus, MaterialRequirementType


class MaterialRequirementCreate(BaseModel):
    well_no: str = Field(min_length=1, max_length=64)
    operation_sheet_id: int | None = None
    material_name: str = Field(min_length=1, max_length=128)
    specification: str | None = Field(default=None, max_length=255)
    quantity: float = Field(default=1, gt=0)
    unit: str = Field(default="件", max_length=32)
    requirement_type: MaterialRequirementType = MaterialRequirementType.NORMAL
    remark: str | None = None


class MaterialRequirementUpdate(BaseModel):
    well_no: str | None = Field(default=None, min_length=1, max_length=64)
    material_name: str | None = Field(default=None, min_length=1, max_length=128)
    specification: str | None = Field(default=None, max_length=255)
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=32)
    requirement_type: MaterialRequirementType | None = None
    status: MaterialRequirementStatus | None = None
    planned_at: datetime | None = None
    remark: str | None = None


class MaterialRequirementQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    well_no: str | None = None
    operation_sheet_id: int | None = None
    status: MaterialRequirementStatus | None = None
    material_name: str | None = None
    requirement_type: MaterialRequirementType | None = None


class MaterialRequirementOut(BaseModel):
    id: int
    well_no: str
    operation_sheet_id: int | None = None
    material_name: str
    specification: str | None = None
    quantity: float
    unit: str
    requirement_type: MaterialRequirementType
    status: MaterialRequirementStatus
    planned_at: datetime | None = None
    delivered_at: datetime | None = None
    arrived_at: datetime | None = None
    used_at: datetime | None = None
    remark: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
