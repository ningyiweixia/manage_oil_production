from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsAlertStatus(str, Enum):
    OPEN = "OPEN"
    PROCESSING = "PROCESSING"
    CLOSED = "CLOSED"


class AnalyticsAlertCreate(BaseModel):
    alert_key: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    severity: str = Field(default="medium", max_length=16)
    source_module: str = Field(min_length=1, max_length=64)
    business_type: str | None = Field(default=None, max_length=64)
    business_id: int | None = None
    status: AnalyticsAlertStatus = AnalyticsAlertStatus.OPEN
    assignee_id: int | None = None
    assignee_name: str | None = Field(default=None, max_length=64)
    remark: str | None = None


class AnalyticsAlertUpdate(BaseModel):
    status: AnalyticsAlertStatus | None = None
    assignee_id: int | None = None
    assignee_name: str | None = Field(default=None, max_length=64)
    remark: str | None = None


class AnalyticsAlertQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    status: AnalyticsAlertStatus | None = None
    severity: str | None = None
    assignee_id: int | None = None
    keyword: str | None = None


class AnalyticsAlertOut(BaseModel):
    id: int
    alert_key: str
    title: str
    message: str
    severity: str
    source_module: str
    business_type: str | None = None
    business_id: int | None = None
    status: AnalyticsAlertStatus
    assignee_id: int | None = None
    assignee_name: str | None = None
    remark: str | None = None
    opened_at: datetime | None = None
    processed_at: datetime | None = None
    closed_at: datetime | None = None
    processed_by_id: int | None = None
    closed_by_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
