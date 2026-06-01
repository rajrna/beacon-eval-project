from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env.local", "../.env.local", "backend/.env.local"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Environment ──────────────────────────────────────────────────────────
    environment: Literal["local", "dev", "prod"] = "local"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://beacon:beacon@localhost:5435/beacon"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    # ── Auth (Microsoft Entra ID) ─────────────────────────────────────────────
    entra_tenant_id: str = Field(default="")
    entra_client_id: str = Field(default="")
    entra_authority: str = Field(default="")
    entra_jwks_uri: str = Field(default="")
    jwt_algorithm: str = "RS256"
    jwt_audience: str = Field(default="")

    # ── Anthropic ─────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="")
    anthropic_default_model: str = "claude-sonnet-4-5"
    anthropic_safety_model: str = "claude-sonnet-4-5"
    anthropic_max_retries: int = 3

    # ── Langfuse ──────────────────────────────────────────────────────────────
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── Azure Blob ────────────────────────────────────────────────────────────
    azure_storage_account_name: str = Field(default="")
    azure_storage_connection_string: str = Field(default="")

    # ── Teams Webhooks ────────────────────────────────────────────────────────
    teams_default_webhook_url: str = Field(default="")

    # ── Eval worker ───────────────────────────────────────────────────────────
    worker_concurrency: int = 4
    eval_batch_size: int = 10
    eval_pass_rate_threshold: float = 0.8

    # ── Rate limits ───────────────────────────────────────────────────────────
    rate_limit_reads_per_minute: int = 100
    rate_limit_writes_per_minute: int = 20
    rate_limit_eval_triggers_per_minute: int = 5

    # ── Safety ────────────────────────────────────────────────────────────────
    crisis_review_sla_minutes: int = 15
    safety_judge_pass_threshold: float = 0.7

    # ── Application Insights ──────────────────────────────────────────────────
    applicationinsights_connection_string: str = Field(default="")

    # ── Computed ──────────────────────────────────────────────────────────────
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_local(self) -> bool:
        return self.environment == "local"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_str(self) -> str:
        return str(self.database_url)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url_str(self) -> str:
        return str(self.redis_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
