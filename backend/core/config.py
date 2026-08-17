from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017/?replicaSet=rs0"
    mongodb_database: str = "whitfield_wms"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    cors_origins_raw: str = Field(default="http://localhost:3000", validation_alias="CORS_ORIGINS")
    trusted_hosts_raw: str = Field(default="localhost,127.0.0.1", validation_alias="TRUSTED_HOSTS")
    auth_required: bool = False
    jwt_secret: str = "development-only-change-me"
    jwt_issuer: str = "whitfield-wms"
    jwt_audience: str = "whitfield-api"
    access_token_minutes: int = Field(default=480, ge=5, le=10080)
    manager_invite_code: str = "WHITFIELD-MANAGER"
    admin_invite_code: str = "WHITFIELD-ADMIN"
    docs_enabled: bool = True
    max_request_body_bytes: int = Field(default=2_000_000, ge=1_024, le=20_000_000)
    rate_limit_requests: int = Field(default=300, ge=10, le=100_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)
    idempotency_ttl_hours: int = Field(default=24, ge=1, le=720)
    mongo_server_selection_timeout_ms: int = Field(default=5_000, ge=500, le=60_000)
    mongo_connect_timeout_ms: int = Field(default=5_000, ge=500, le=60_000)
    mongo_max_pool_size: int = Field(default=50, ge=5, le=500)
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-5.6-luna"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    ai_provider: str = Field(default="auto", pattern="^(auto|gemini|openai|local)$")
    stripe_secret_key: str | None = None
    stripe_publishable_key: str | None = None
    stripe_webhook_secret: str | None = None
    knowledge_max_file_bytes: int = Field(default=1_500_000, ge=10_000, le=10_000_000)
    knowledge_top_k: int = Field(default=5, ge=1, le=12)

    model_config = SettingsConfigDict(env_file=PROJECT_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts_raw.split(",") if host.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @model_validator(mode="after")
    def validate_security_settings(self):
        if self.is_production:
            if not self.auth_required:
                raise ValueError("AUTH_REQUIRED must be true in production")
            if len(self.jwt_secret.encode("utf-8")) < 32 or self.jwt_secret == "development-only-change-me":
                raise ValueError("JWT_SECRET must be a unique secret of at least 32 bytes in production")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS origins are forbidden in production")
            if self.docs_enabled:
                raise ValueError("DOCS_ENABLED must be false in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
