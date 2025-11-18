# Production configuration for 100k users
from pydantic_settings import BaseSettings

class ProductionSettings(BaseSettings):
    # Database Connection Pool (Critical for 100k users)
    DB_POOL_SIZE: int = 50
    DB_MAX_OVERFLOW: int = 100
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    
    # Redis Cache (Essential for performance)
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 300
    
    # Background Jobs (Celery/RQ)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Rate Limiting (Prevent abuse)
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 100
    
    # AI Service Optimization
    AI_ASYNC_PROCESSING: bool = True
    AI_QUEUE_SIZE: int = 1000
    AI_TIMEOUT: int = 10  # Reduced from 30
    
    # Pagination (Prevent memory issues)
    MAX_PAGE_SIZE: int = 50
    DEFAULT_PAGE_SIZE: int = 20
    
    # Monitoring
    ENABLE_METRICS: bool = True
    LOG_LEVEL: str = "WARNING"  # Reduce log volume

production_settings = ProductionSettings()