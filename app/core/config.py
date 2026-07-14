from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "采油二厂井下作业管理系统"
    environment: Literal["local", "dev", "test", "prod"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    postgres_server: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str
    postgres_db: str = "manage_factory"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    refresh_token_expire_minutes: int = 10080
    redis_url: str | None = None
    sqlalchemy_database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    cors_allow_origins: str = "http://127.0.0.1:8000,http://localhost:8000"
    auth_whitelist: str = "/docs,/docs/oauth2-redirect,/redoc,/openapi.json,/health,/api/v1/auth/login,/api/v1/auth/refresh,/api/v1/auth/logout,/api/v1/a5/callback"
    admin_initial_password: str | None = None
    # A5 系统集成配置
    a5_base_url: str = ""
    a5_api_key: str = ""
    a5_api_secret: str = ""
    a5_ip_whitelist: str = ""
    a5_mock_enabled: bool = False
    a5_mock_frontend_base_url: str = "http://127.0.0.1:5173"
    a5_timeout_seconds: float = 30.0
    alert_webhook_url: str = ""
    contractor_system_base_url: str = ""
    contractor_system_token: str = ""
    contractor_system_timeout: float = 5.0
    contractor_system_mock_enabled: bool = True
    @computed_field
    @property
    def database_url(self) -> str:
        if self.sqlalchemy_database_url:
            return self.sqlalchemy_database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def auth_whitelist_paths(self) -> set[str]:
        return {item.strip() for item in self.auth_whitelist.split(",") if item.strip()}

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_allow_origins.split(",") if item.strip()]

    @property
    def a5_allowed_ips(self) -> set[str]:
        return {item.strip() for item in self.a5_ip_whitelist.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
