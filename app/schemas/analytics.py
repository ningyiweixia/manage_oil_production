from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DataQualitySeverity = Literal["low", "medium", "high"]


class DataQualityIssueOut(BaseModel):
    rule_code: str
    title: str
    severity: DataQualitySeverity
    message: str
    entity_type: str
    entity_id: int | None = None
    well_no: str | None = None
    team_name: str | None = None
    suggestion: str | None = None


class DataQualitySummaryOut(BaseModel):
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    total_issues: int
    severity_counts: dict[str, int]
    issues: list[DataQualityIssueOut]
    scope: dict[str, object] = Field(default_factory=dict)
