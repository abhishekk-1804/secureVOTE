"""
SecureVOTE Backend Configuration.

Loads settings from environment variables / .env file.
This is a research-oriented prototype Ã¢â‚¬â€ not production election infrastructure.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./securevote.db",
        description="Database connection URL. Use postgresql+asyncpg:// for PostgreSQL.",
    )

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="dev-secret-change-me-in-production",
        description="Secret key for JWT token signing. MUST be changed in deployment.",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Signing key for election manifests (backend-only per spec Ã‚Â§9)
    signing_key_path: str = Field(
        default="./signing_key.pem",
        description="Path to PEM-encoded signing key for election manifests.",
    )

    # Serial device (Phase 2+)
    serial_port: str = "COM3"
    serial_baud: int = 9600

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
