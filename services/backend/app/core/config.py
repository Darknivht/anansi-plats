"""
Anansi Configuration — Pydantic Settings loading from environment / .env file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ─── Database ───────────────────────────────────────────────────────────────────


class DatabaseSettings(BaseSettings):
    """PostgreSQL with pgvector connection settings."""

    model_config = SettingsConfigDict(env_prefix="DATABASE_", env_file=".env", extra="ignore")

    url: str = Field(
        default="postgresql+asyncpg://anansi:anansi@localhost:5432/anansi",
        description="PostgreSQL async connection string (with pgvector support)",
    )
    pool_size: int = Field(default=20, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0)
    pool_pre_ping: bool = True
    echo: bool = Field(default=False, description="SQL echo for debugging")
    connect_timeout: int = Field(default=10, ge=1)
    ssl_mode: str = Field(default="prefer", description="SSL mode for the connection")

    @property
    def sync_url(self) -> str:
        """Return a sync-style URL (useful for Alembic or one-off scripts)."""
        return self.url.replace("+asyncpg", "")


# ─── Redis ───────────────────────────────────────────────────────────────────────


class RedisSettings(BaseSettings):
    """Redis connection settings (cache, session store, rate limiter)."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", env_file=".env", extra="ignore")

    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    socket_timeout: int = Field(default=5, ge=1)
    socket_connect_timeout: int = Field(default=5, ge=1)
    retry_on_timeout: bool = True
    max_connections: int = Field(default=50, ge=1)
    health_check_interval: int = Field(default=30, ge=1)
    decode_responses: bool = True


# ─── Neo4j ──────────────────────────────────────────────────────────────────────


class Neo4jSettings(BaseSettings):
    """Neo4j graph database settings for the Second Brain knowledge web."""

    model_config = SettingsConfigDict(env_prefix="NEO4J_", env_file=".env", extra="ignore")

    url: str = Field(default="bolt://localhost:7687", description="Neo4j bolt connection URL")
    user: str = Field(default="neo4j")
    password: str = Field(default="anansi")
    database: str = Field(default="anansi", description="Neo4j database name")
    max_connection_pool_size: int = Field(default=50, ge=1)
    connection_acquisition_timeout: int = Field(default=60, ge=1)
    max_transaction_retry_time: int = Field(default=30, ge=1)


# ─── JWT ─────────────────────────────────────────────────────────────────────────


class JWTSettings(BaseSettings):
    """JWT configuration — uses RS256 with a 2048-bit private key."""

    model_config = SettingsConfigDict(env_prefix="JWT_", env_file=".env", extra="ignore")

    private_key: str = Field(
        default="",
        description="RSA private key (PEM). If empty a development key is generated at startup.",
    )
    public_key: str = Field(
        default="",
        description="RSA public key (PEM). Derived from private-key if empty.",
    )
    algorithm: str = Field(default="RS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)
    issuer: str = Field(default="anansi.ai")
    audience: str = Field(default="anansi-api")


# ─── OAuth ───────────────────────────────────────────────────────────────────────


class OAuthSettings(BaseSettings):
    """OAuth 2.0 provider settings."""

    model_config = SettingsConfigDict(env_prefix="OAUTH_", env_file=".env", extra="ignore")

    google_client_id: str = Field(default="", description="Google OAuth client ID")
    google_client_secret: str = Field(default="", description="Google OAuth client secret")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/google/callback",
    )

    github_client_id: str = Field(default="", description="GitHub OAuth client ID")
    github_client_secret: str = Field(default="", description="GitHub OAuth client secret")
    github_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/github/callback",
    )


# ─── AI Provider ─────────────────────────────────────────────────────────────────


class AISettings(BaseSettings):
    """AI provider configuration — model-agnostic layer."""

    model_config = SettingsConfigDict(env_prefix="AI_", env_file=".env", extra="ignore")

    default_provider: Literal["anthropic", "openai", "ollama"] = Field(default="anthropic")
    anthropic_api_key: str = Field(default="")
    anthropic_default_model: str = Field(default="claude-sonnet-4-20250514")
    openai_api_key: str = Field(default="")
    openai_default_model: str = Field(default="gpt-4o")
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_default_model: str = Field(default="llama3")

    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(default=1536, ge=384, le=3072)

    max_tokens: int = Field(default=4096, ge=256, le=128_000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    request_timeout: int = Field(default=120, ge=10)


# ─── WhatsApp ────────────────────────────────────────────────────────────────────


class WhatsAppSettings(BaseSettings):
    """WhatsApp Business API configuration."""

    model_config = SettingsConfigDict(env_prefix="WHATSAPP_", env_file=".env", extra="ignore")

    phone_number_id: str = Field(default="", description="WhatsApp Business phone number ID")
    business_account_id: str = Field(default="", description="WABA ID")
    api_token: str = Field(default="", description="WhatsApp Cloud API token")
    api_version: str = Field(default="v22.0")
    webhook_verify_token: str = Field(default="anansi_webhook_verify_2026")
    base_url: str = Field(default="https://graph.facebook.com")


# ─── Payment (Stripe) ────────────────────────────────────────────────────────────


class PaymentSettings(BaseSettings):
    """Payment provider settings (Stripe primary, Paystack/Flutterwave as fallback)."""

    model_config = SettingsConfigDict(env_prefix="PAYMENT_", env_file=".env", extra="ignore")

    stripe_secret_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    stripe_price_free: str = Field(default="")
    stripe_price_pro: str = Field(default="")
    stripe_price_business: str = Field(default="")
    currency: str = Field(default="usd")

    paystack_secret_key: str = Field(default="")
    flutterwave_secret_key: str = Field(default="")


# ─── Storage ─────────────────────────────────────────────────────────────────────


class StorageSettings(BaseSettings):
    """S3-compatible object storage settings (MinIO / Cloudflare R2)."""

    model_config = SettingsConfigDict(env_prefix="STORAGE_", env_file=".env", extra="ignore")

    endpoint_url: str = Field(default="http://localhost:9000")
    access_key_id: str = Field(default="minioadmin")
    secret_access_key: str = Field(default="minioadmin")
    region: str = Field(default="auto")
    bucket: str = Field(default="anansi")
    public_url_base: str = Field(default="http://localhost:9000/anansi")
    max_file_size_mb: int = Field(default=50, ge=1, le=500)


# ─── Monitoring ──────────────────────────────────────────────────────────────────


class MonitoringSettings(BaseSettings):
    """Observability — Sentry, OpenTelemetry, logging."""

    model_config = SettingsConfigDict(env_prefix="MONITORING_", env_file=".env", extra="ignore")

    sentry_dsn: str = Field(default="")
    sentry_environment: str = Field(default="development")
    sentry_traces_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    otel_service_name: str = Field(default="anansi-api")
    otel_endpoint: str = Field(default="http://localhost:4318")
    log_level: str = Field(default="INFO")
    log_format: Literal["json", "console"] = Field(default="json")


# ─── Rate Limiting ───────────────────────────────────────────────────────────────


class RateLimitSettings(BaseSettings):
    """Default rate-limit tiers (token-bucket)."""

    model_config = SettingsConfigDict(env_prefix="RATE_LIMIT_", env_file=".env", extra="ignore")

    free_max_requests: int = Field(default=100, description="Requests per minute for free tier")
    free_window_seconds: int = Field(default=60)

    pro_max_requests: int = Field(default=500)
    pro_window_seconds: int = Field(default=60)

    business_max_requests: int = Field(default=1000)
    business_window_seconds: int = Field(default=60)


# ─── CORS ────────────────────────────────────────────────────────────────────────


class CORSSettings(BaseSettings):
    """Allowed origins for CORS middleware."""

    model_config = SettingsConfigDict(env_prefix="CORS_", env_file=".env", extra="ignore")

    allow_origins: list[str] = Field(
        default=[
            "https://anansi.ai",
            "https://app.anansi.ai",
            "https://www.anansi.ai",
            "http://localhost:3000",
        ],
    )
    allow_credentials: bool = True
    allow_methods: list[str] = Field(default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    allow_headers: list[str] = Field(default=["*"])


# ─── App ─────────────────────────────────────────────────────────────────────────


class AppSettings(BaseSettings):
    """General application settings."""

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    name: str = "Anansi"
    version: str = "2.0.0"
    debug: bool = True
    environment: Literal["development", "staging", "production"] = Field(default="development")
    api_prefix: str = "/api"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"

    bcrypt_rounds: int = Field(default=12, ge=4, le=31)
    request_id_header: str = Field(default="X-Request-ID")


# ─── Composite Settings ──────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """Top-level settings aggregating all sub-settings."""

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="ignore")

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    oauth: OAuthSettings = Field(default_factory=OAuthSettings)
    ai: AISettings = Field(default_factory=AISettings)
    whatsapp: WhatsAppSettings = Field(default_factory=WhatsAppSettings)
    payment: PaymentSettings = Field(default_factory=PaymentSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)


# ─── Global singleton ────────────────────────────────────────────────────────────

settings = Settings()  # type: ignore[call-arg]

__all__ = [
    "Settings",
    "settings",
    "AppSettings",
    "DatabaseSettings",
    "RedisSettings",
    "Neo4jSettings",
    "JWTSettings",
    "OAuthSettings",
    "AISettings",
    "WhatsAppSettings",
    "PaymentSettings",
    "StorageSettings",
    "MonitoringSettings",
    "RateLimitSettings",
    "CORSSettings",
]
