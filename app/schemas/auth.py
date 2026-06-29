from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.rbac import MenuOut, PermissionOut, RoleOut


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
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


class AccountCancelRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


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
