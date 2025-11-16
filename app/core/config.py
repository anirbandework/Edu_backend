# app/core/config.py
"""Application configuration using Pydantic."""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret_key: str

    app_version: str = '1.0.0'
    environment: str = 'development'
    log_level: str = 'info'
    allowed_origins: List[str] = ['*']

    model_config = {
        'env_file': '.env',
        'extra': 'ignore'
    }

settings = Settings()
