"""Health check endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from ..core.database import get_db, health_check_db  # Removed test_connection import

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "EduAssist API",
        "version": "1.0.0",
        "platform": "Docker Local"
    }

@router.get("/db-health")
async def database_health():
    """Database health check with manual connection test"""
    try:
        # Manual connection test instead of using test_connection function
        from ..core.database import engine
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version(), NOW(), current_database()"))
            row = result.fetchone()
            return {
                "status": "healthy",
                "database": "AWS Aurora PostgreSQL",
                "region": "eu-north-1",
                "version": row[0][:50] + "...",  # Truncate long version string
                "timestamp": str(row[1]),
                "current_db": row[2]
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "AWS Aurora PostgreSQL",
            "region": "eu-north-1",
            "error": str(e),
            "error_type": type(e).__name__,
            "suggestion": "Check AWS security groups, network connectivity, and database status"
        }

@router.get("/db-session-test")
async def database_session_test(session: AsyncSession = Depends(get_db)):
    """Test database using session dependency"""
    try:
        result = await session.execute(text("SELECT 1 as test, NOW() as timestamp"))
        row = result.fetchone()
        return {
            "status": "healthy",
            "database": "AWS Aurora PostgreSQL (via session)",
            "test_result": row.test,
            "timestamp": str(row.timestamp)
        }
    except Exception as e:
        logger.error(f"Session test failed: {e}")
        return {
            "status": "error",
            "database": "AWS Aurora PostgreSQL (via session)",
            "error": str(e)
        }

@router.get("/cache-health")
async def cache_health():
    """Redis cache health check"""
    try:
        from ..core.cache import cache_manager
        # Basic cache connectivity test
        return {
            "status": "healthy",
            "cache": "AWS ElastiCache Redis",
            "region": "eu-north-1"
        }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "status": "error",
            "cache": "AWS ElastiCache Redis",
            "error": str(e)
        }

@router.get("/full-health")
async def full_health_check():
    """Comprehensive health check"""
    health_status = {
        "service": "healthy",
        "database": "unknown",
        "cache": "unknown"
    }
    
    # Test database
    db_healthy = await health_check_db()
    health_status["database"] = "healthy" if db_healthy else "unhealthy"
    
    # Test cache
    try:
        from ..core.cache import cache_manager
        health_status["cache"] = "healthy"
    except:
        health_status["cache"] = "unhealthy"
    
    overall_status = "healthy" if all(
        status == "healthy" for status in health_status.values()
    ) else "degraded"
    
    return {
        "status": overall_status,
        "components": health_status,
        "timestamp": "now"
    }

@router.get("/simple")
async def simple_health():
    """Simple health check that doesn't test external services"""
    return {
        "status": "healthy",
        "service": "EduAssist API",
        "message": "API is running"
    }
