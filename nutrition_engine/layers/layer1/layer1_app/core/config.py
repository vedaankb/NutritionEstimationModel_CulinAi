"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Optional

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    api_workers: int = 4
    
    # Database
    database_url: PostgresDsn
    
    # Security
    secret_key: str
    api_key_header: str = "X-API-Key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # USDA API
    usda_api_key: Optional[str] = None
    usda_api_url: str = "https://api.nal.usda.gov/fdc/v1"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Sentry
    sentry_dsn: Optional[str] = None
    
    # Environment
    environment: str = "development"
    
    # Application
    app_name: str = "Nutrition Calculator API"
    app_version: str = "1.0.0"
    debug: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        """Ensure database URL is properly formatted."""
        if isinstance(v, str):
            return v
        return str(v)

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
