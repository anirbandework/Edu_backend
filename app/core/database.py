"""Database connection and session management using SQLAlchemy."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy import text
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Production-ready Aurora PostgreSQL configuration
engine = create_async_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,  # Wait 30s for connection from pool
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Verify connections before use
    echo=(settings.environment == 'development'),
    # Aurora-optimized connection arguments
    connect_args={
        "command_timeout": 30,  # Query timeout in seconds
        "server_settings": {
            "jit": "off",  # Disable JIT for faster connection startup
            "application_name": "eduassist_api",
            "statement_timeout": "30s",  # Database-level query timeout
        }
    }
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    expire_on_commit=False, 
    class_=AsyncSession,
    autoflush=False,  # Manual control over flushing
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with proper error handling"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

async def health_check_db():
    """Fast health check with timeout handling"""
    try:
        async with engine.connect() as conn:
            # Quick test query with timeout
            result = await conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

async def execute_raw_sql(query: str, params: dict = None):
    """Execute raw SQL with error handling"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(query), params or {})
            return result.fetchall()
    except Exception as e:
        logger.error(f"Raw SQL execution failed: {e}")
        raise

# Connection test function for debugging
async def test_connection():
    """Test database connection with detailed error info"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version(), NOW(), current_database()"))
            row = result.fetchone()
            return {
                "status": "success",
                "version": row[0],
                "timestamp": str(row[1]),
                "database": row[2]
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "type": type(e).__name__
        }
