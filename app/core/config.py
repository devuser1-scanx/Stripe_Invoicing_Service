from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ScanX Billing Service"
    app_version: str = "0.1.0"
    environment: Literal["local", "staging", "production", "test"] = "local"
    log_level: str = "INFO"

    # Cloud SQL
    instance_connection_name: str
    db_user: str
    db_password: SecretStr
    db_name: str = "scanx_app"
    db_ip_type: Literal["PUBLIC", "PRIVATE"] = "PUBLIC"

    # SQLAlchemy pool
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=2, ge=0, le=50)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60)

    # Local TCP fallback, useful with Cloud SQL Auth Proxy.
    use_tcp_database: bool = False
    db_host: str = "127.0.0.1"
    db_port: int = 5432


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
