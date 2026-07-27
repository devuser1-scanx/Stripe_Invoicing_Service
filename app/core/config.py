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

    # Application
    app_name: str = "ScanX Billing Service"
    app_version: str = "0.4.0"

    environment: Literal[
        "local",
        "staging",
        "production",
        "test",
    ] = "local"

    log_level: str = "INFO"

    # Cloud SQL
    instance_connection_name: str
    db_user: str
    db_password: SecretStr
    db_name: str = "scanx_app"

    db_ip_type: Literal[
        "PUBLIC",
        "PRIVATE",
    ] = "PUBLIC"

    db_pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
    )

    db_max_overflow: int = Field(
        default=2,
        ge=0,
        le=50,
    )

    db_pool_recycle_seconds: int = Field(
        default=1800,
        ge=60,
    )

    # Local database fallback
    use_tcp_database: bool = False
    db_host: str = "127.0.0.1"
    db_port: int = Field(
        default=5432,
        ge=1,
        le=65535,
    )

    # Stripe
    stripe_secret_key: SecretStr
    stripe_default_currency: str = "usd"

    stripe_invoice_collection_method: Literal[
        "send_invoice",
        "charge_automatically",
    ] = "send_invoice"

    # Google Cloud
    gcp_project_id: str
    gcp_region: str = "us-central1"

    # Cloud Tasks
    cloud_tasks_queue: str = "scanx-invoice-primary"
    billing_service_url: str
    cloud_tasks_invoker_service_account: str

    invoice_delay_seconds: int = Field(
        default=600,
        ge=0,
        le=86400,
    )

    # Nightly reconciliation
    reconciliation_lookback_days: int = Field(
        default=30,
        ge=1,
        le=365,
    )

    reconciliation_batch_size: int = Field(
        default=250,
        ge=1,
        le=1000,
    )

    reconciliation_task_delay_seconds: int = Field(
        default=0,
        ge=0,
        le=3600,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()