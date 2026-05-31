from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PermissionOut(BaseModel):
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class RoleOut(BaseModel):
    code: str
    name: str
    permissions: list[PermissionOut] = []

    model_config = ConfigDict(from_attributes=True)


class CurrentUserOut(BaseModel):
    id: int
    username: str
    full_name: str
    department: str | None = None
    roles: list[RoleOut] = []

    model_config = ConfigDict(from_attributes=True)
