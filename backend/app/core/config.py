"""Application configuration and typed environment settings."""

import os
from functools import lru_cache
from typing import List, Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application Metadata
    PROJECT_NAME: str = Field(
        default="Converge AI — Conference Agent Network",
        description="Public human-readable service name",
    )
    VERSION: str = Field(
        default="0.1.0",
        description="Semantic application version",
    )
    ENVIRONMENT: Literal["development", "test", "production"] = Field(
        default="development",
        description="Current runtime environment",
    )

    # API Routing
    API_V1_PREFIX: str = Field(
        default="/converge-api/v1",
        description="Unified external API gateway prefix",
    )

    # Server Network Bindings
    HOST: str = Field(
        default="127.0.0.1",
        description="Local host interface to bind application server",
    )
    PORT: int = Field(
        default=8030,
        description="Port for application server",
    )

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Application logging verbosity",
    )

    # Proxy and Security
    TRUSTED_PROXIES: List[str] = Field(
        default=["127.0.0.1", "::1"],
        description="List of trusted reverse proxy IP addresses",
    )

    # Background Agent Task Worker (Phase 6)
    AGENT_WORKER_ENABLED: bool = Field(
        default=False,
        description="Whether to run the background agent execution worker loop inside application lifespan",
    )
    AGENT_WORKER_POLL_INTERVAL: float = Field(
        default=1.0,
        description="Polling interval in seconds for background agent worker queue",
    )
    AGENT_AUTONOMOUS_ENABLED: bool = Field(
        default=False,
        description="Whether accepting a conversation automatically schedules autonomous agent representative dialogue",
    )

    # Database Configuration (WS-3)
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Async PostgreSQL connection string for runtime application queries",
    )
    MIGRATION_DATABASE_URL: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection string for Alembic schema migrations (converge_ai_owner)",
    )
    TEST_DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Isolated test database connection string (converge_ai_test)",
    )
    TEST_MIGRATION_URL: Optional[str] = Field(
        default=None,
        description="Isolated test migration connection string (converge_ai_owner)",
    )
    DB_POOL_SIZE: int = Field(
        default=5,
        description="SQLAlchemy connection pool base size",
    )
    DB_MAX_OVERFLOW: int = Field(
        default=10,
        description="SQLAlchemy connection pool max overflow",
    )
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        description="SQLAlchemy pool timeout in seconds",
    )
    DB_ECHO: bool = Field(
        default=False,
        description="SQLAlchemy SQL echo (enable for debug query logging)",
    )

    # Dedicated Administration Credentials (Phase 2)
    ADMIN_USERNAME: str = Field(
        default="admin",
        description="Administrative user username",
    )
    ADMIN_PASSWORD: Optional[str] = Field(
        default=None,
        description="Administrative user password for initial provisioning and authentication",
    )

    # Google Maps & Geolocation
    GOOGLE_MAPS_SERVER_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Maps Server API Key for backend traffic & routes queries",
    )

    # Email Service Configuration (Quote Subphase 1)
    EMAIL_BACKEND: Literal["console", "smtp", "resend", "sendgrid"] = Field(
        default="console",
        description="Active email delivery backend provider ('console' for test/dev, 'smtp' for production relay)",
    )
    EMAIL_SENDER_ADDRESS: str = Field(
        default="sanjana.mahajan@sofueled.com",
        description="Default sender email address for commercial quotations and alerts",
    )
    EMAIL_SENDER_NAME: str = Field(
        default="Converge AI Commercial Network",
        description="Display name for outgoing system and quote emails",
    )
    SMTP_HOST: Optional[str] = Field(
        default="smtp.gmail.com",
        description="SMTP server hostname",
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port (587 for STARTTLS)",
    )
    SMTP_USE_TLS: bool = Field(
        default=True,
        description="Whether to initiate STARTTLS encryption",
    )
    SMTP_USERNAME: Optional[str] = Field(
        default=None,
        description="SMTP authentication username (e.g. Google Workspace address)",
    )
    SMTP_PASSWORD: Optional[str] = Field(
        default=None,
        description="SMTP authentication password or app password",
    )
    RESEND_API_KEY: Optional[str] = Field(
        default=None,
        description="Optional API key if EMAIL_BACKEND=resend",
    )

    # Media & Digital Brochure Storage (Phase 1)
    UPLOAD_DIR: str = Field(
        default="/opt/apps/converge-ai/uploads" if os.path.exists("/opt/apps/converge-ai/uploads") else "./uploads",
        description="Root directory for uploaded media and digital brochures",
    )
    BROCHURE_MAX_FILE_SIZE_MB: int = Field(
        default=25,
        description="Maximum allowed file size per brochure page in MB",
    )

    @field_validator("API_V1_PREFIX")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        """Ensure API prefix starts with / and has no trailing slash."""
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            cleaned = f"/{cleaned}"
        if cleaned.endswith("/") and len(cleaned) > 1:
            cleaned = cleaned.rstrip("/")
        if cleaned == "/":
            raise ValueError("API prefix cannot be empty or root '/'")
        return cleaned

    @field_validator("PORT")
    @classmethod
    def validate_port_range(cls, value: int) -> int:
        """Validate port range for unprivileged server binding."""
        if not (1024 <= value <= 65535):
            raise ValueError(f"Port must be between 1024 and 65535. Received: {value}")
        return value

    def is_production(self) -> bool:
        """Return True if running in production."""
        return self.ENVIRONMENT == "production"

    def is_test(self) -> bool:
        """Return True if running under test suite."""
        return self.ENVIRONMENT == "test"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()

settings = get_settings()
