from pydantic_settings import BaseSettings
from typing import Optional

class AssessmentSettings(BaseSettings):
    # AI Configuration - Optimized for production
    AI_MAX_TOKENS: int = 2000  # Reduced for faster responses
    AI_TEMPERATURE: float = 0.3
    AI_TIMEOUT: int = 15  # Reduced timeout
    AI_MODEL: str = "sonar"
    AI_CONCURRENT_REQUESTS: int = 10  # Limit concurrent AI calls
    
    # Assessment Configuration
    PASSING_THRESHOLD: int = 60
    DEFAULT_TIME_LIMIT: int = 30
    MAX_QUESTIONS_PER_QUIZ: int = 50
    MAX_ATTEMPTS_PER_QUIZ: int = 3
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 100
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: list = [".pdf", ".doc", ".docx"]
    
    # Performance
    QUERY_TIMEOUT: int = 30
    CACHE_TTL: int = 300  # 5 minutes
    
    class Config:
        env_prefix = "ASSESSMENT_"

assessment_settings = AssessmentSettings()