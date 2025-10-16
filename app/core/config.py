# app/core/config.py
"""Application configuration settings."""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Info
    app_name: str = "EduAssist API Gateway"
    app_version: str = "4.0.0"
    environment: str = "development"
    
    # Database settings - Async PostgreSQL
    database_url: str = "postgresql+asyncpg://eduassist:dev_password@localhost:5432/eduassist"
    
    # Redis settings for caching
    redis_url: str = "redis://localhost:6379"
    
    # JWT Security
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AI/ML Settings
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # AWS Settings (if needed)
    aws_region: Optional[str] = os.getenv("AWS_REGION")
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    # Cache TTL Settings (seconds)
    cache_ttl_short: int = 180    # 3 minutes - for lists
    cache_ttl_medium: int = 600   # 10 minutes - for individual items
    cache_ttl_long: int = 1800    # 30 minutes - for stats/analytics
    
    # Logging
    log_level: str = "info"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
