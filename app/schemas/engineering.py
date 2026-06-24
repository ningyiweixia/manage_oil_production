from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EngineeringDesignCreate(BaseModel):
    project_id: int = Field(ge=1)
    well_no: str = Field(min_length=1, max_length=64)
    template_type: str = Field(default="word", pattern=r"^(word|excel)$")


class EngineeringDesignUpdate(BaseModel):
    remark: str | None = None


class EngineeringDesignQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    well_no: str | None = None
    project_id: int | None = None


class EngineeringDesignOut(BaseModel):
    id: int
    project_id: int | None = None
    well_no: str
    version: str
    minio_bucket: str
    minio_object_key: str
    checksum: str | None = None
    remark: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuleCheckResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DesignGenerateOut(BaseModel):
    design: EngineeringDesignOut
    rule_check: RuleCheckResult
