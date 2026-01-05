"""
config.py

Centralized application configuration.

Responsibilities:
- Environment variable loading
- Application-wide settings
- Security configuration
- Runtime behavior flags

This module MUST NOT import FastAPI or application logic.
"""

from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    """
    Application settings model.

    Loaded once and cached for the lifetime of the process.
    """

    # Application
    APP_NAME: str = "Agentic UI Platform"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE_ME")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = 60 * 60 * 24  # 24 hours

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Observability
    ENABLE_TRACING: bool = True

    # Runtime
    MAX_CONCURRENT_RUNS: int = 50


@lru_cache
def get_settings() -> Settings:
    """
    Return cached application settings.

    Using LRU cache ensures:
    - Single instantiation
    - Thread safety
    - Fast access
    """
    return Settings()

# **This is the key:** instantiate a global singleton
settings = get_settings()

