from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# 应用配置
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    env: str = "dev"
    database_url: str = "postgresql+psycopg://lexpilot:lexpilot@localhost:55432/lexpilot"
    redis_url: str = "redis://localhost:56379/0"

    jwt_secret: str = "dev-only-change-me-please-use-32-bytes-minimum"
    jwt_algorithm: str = "HS256"
    jwt_active_kid: str = "v1"
    jwt_keys: dict[str, str] = Field(default_factory=dict)
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    refresh_cookie_name: str = "lexpilot_refresh"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    login_rate_limit: int = 5
    login_rate_window_seconds: int = 900

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    @property
    def jwt_keyring(self) -> dict[str, str]:
        return self.jwt_keys or {self.jwt_active_kid: self.jwt_secret}


@lru_cache
def get_settings() -> Settings:
    return Settings()
