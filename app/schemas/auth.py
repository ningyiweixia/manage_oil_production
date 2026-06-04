from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rbac import MenuOut, PermissionOut, RoleOut


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    token: TokenResponse
    user: "CurrentUserOut"
    permissions: list[str]
    menus: list[MenuOut]


class CurrentUserOut(BaseModel):
    id: int
    username: str
    full_name: str
    department: str | None = None
    roles: list[RoleOut] = []
    permissions: list[PermissionOut] = []
    menus: list[MenuOut] = []

    model_config = ConfigDict(from_attributes=True)
