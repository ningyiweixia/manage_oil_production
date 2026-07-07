from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IdsPayload(BaseModel):
    ids: list[int] = Field(default_factory=list)


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=64)
    department: str | None = Field(default=None, max_length=128)
    mobile: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=128)
    is_active: bool = True
    role_ids: list[int] = Field(default_factory=list)
    extra_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        checks = (
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
        if not all(checks):
            raise ValueError("Password must include uppercase, lowercase, number, and special character")
        return value


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=64)
    department: str | None = Field(default=None, max_length=128)
    mobile: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=128)
    is_active: bool = True
    extra_config: dict[str, Any] = Field(default_factory=dict)


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    department: str | None = None
    mobile: str | None = None
    email: str | None = None
    is_active: bool
    is_superuser: bool
    role_ids: list[int] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    extra_config: dict[str, Any] = Field(default_factory=dict)


class RoleUpdate(RoleCreate):
    pass


class RoleOut(BaseModel):
    id: int
    name: str
    code: str
    description: str | None = None
    is_active: bool
    menu_ids: list[int] = []
    permission_ids: list[int] = []

    model_config = ConfigDict(from_attributes=True)


class MenuCreate(BaseModel):
    parent_id: int | None = None
    title: str = Field(min_length=1, max_length=64)
    route_name: str = Field(min_length=1, max_length=128)
    route_path: str = Field(min_length=1, max_length=255)
    component: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=64)
    sort_order: int = 0
    is_visible: bool = True
    is_active: bool = True
    meta: dict[str, Any] = Field(default_factory=dict)


class MenuUpdate(MenuCreate):
    pass


class MenuOut(BaseModel):
    id: int
    parent_id: int | None = None
    title: str
    route_name: str
    route_path: str
    component: str | None = None
    icon: str | None = None
    sort_order: int
    is_visible: bool
    is_active: bool
    meta: dict[str, Any]
    children: list["MenuOut"] = []

    model_config = ConfigDict(from_attributes=True)


class PermissionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=255)
    method: str = Field(min_length=1, max_length=16)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    extra_config: dict[str, Any] = Field(default_factory=dict)


class PermissionUpdate(PermissionCreate):
    pass


class PermissionOut(BaseModel):
    id: int
    name: str
    code: str
    path: str
    method: str
    description: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class OperationLogOut(BaseModel):
    id: int
    trace_id: str | None = None
    user_id: int | None = None
    username: str | None = None
    ip_address: str | None = None
    method: str
    path: str
    operation: str | None = None
    status_code: int | None = None
    response_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportMetricOut(BaseModel):
    name: str
    status: str
    value: str | int | float | None = None
    description: str | None = None


class SystemSupportOverviewOut(BaseModel):
    runtime_monitoring: list[SupportMetricOut] = []
    security_controls: list[SupportMetricOut] = []
    audit_traceability: list[SupportMetricOut] = []
    backup_recovery: list[SupportMetricOut] = []
    message_alerts: list[SupportMetricOut] = []
    data_scope: list[SupportMetricOut] = []


class ApprovalLogOut(BaseModel):
    id: int
    business_type: str
    business_id: int
    node_code: str
    action: str
    comment: str | None = None
    operator_id: int | None = None
    operator_ip: str | None = None
    before_snapshot: dict[str, Any] | None = None
    after_snapshot: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
