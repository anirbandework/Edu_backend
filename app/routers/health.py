# services/api-gateway/app/routers/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from sqlalchemy import text  # Import text function
from ..core.database import get_db

router = APIRouter(tags=["Health"])

@router.get("/health")
async async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection with proper text() wrapper
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "message": "EduAssist API Gateway is running successfully",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "database": "disconnected",
            "error": str(e),
            "message": "Database connection failed"
        }
