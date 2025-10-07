"""Database connection and session management using SQLAlchemy."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy import text

from .config import settings

# Aurora PostgreSQL optimized settings
engine = create_async_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=10,
    pool_recycle=1800,  # 30 minutes
    pool_pre_ping=True,
    echo=(settings.environment == 'development'),
    # Aurora-specific optimizations (only use supported asyncpg parameters)
    connect_args={
        "server_settings": {
            "jit": "off",  # Disable JIT for faster connections
            "application_name": "eduassist_api"
        }
    }
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    expire_on_commit=False, 
    class_=AsyncSession,
    autoflush=False,  # Reduce auto-flushing for better performance
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Health check function
async def health_check_db():
    """Fast health check without full connection overhead"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

# Optional: Function to execute raw SQL (if needed)
async def execute_raw_sql(query: str, params: dict = None):
    async with engine.connect() as conn:
        result = await conn.execute(text(query), params or {})
        return result.fetchall()
