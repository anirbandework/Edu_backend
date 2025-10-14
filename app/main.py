# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time
from sqlalchemy import text  # ADDED MISSING IMPORT


from .core.config import settings
from .core.database import engine, background_engine, close_db_connections, get_pool_status
from .core.cache import cache_manager
from .routers.health import router as health_router
from .routers.tenant import router as tenant_router
from .routers.school_authority import router as school_authority_router
from .routers.school_authority_management.teacher import router as teacher_router
from .routers.school_authority_management.student import router as student_router
from .routers.school_authority_management.class_management import router as class_router
from .routers.school_authority_management.enrollment import router as enrollment_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced application lifespan with bulk operations support"""
    logger.info("Starting EduAssist Backend API")
    
    # Initialize cache manager
    try:
        await cache_manager.initialize()
        logger.info("Cache manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")
        # Don't fail startup if cache is unavailable
    
    # Test database connections for both engines
    try:
        # Test main engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Main database engine connected successfully")
        
        # Test background engine
        async with background_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Background database engine connected successfully")
        
        # Log initial pool status
        pool_status = await get_pool_status()
        logger.info(f"Database pool status: {pool_status}")
        
    except Exception as e:
        logger.error(f"Database connection failed during startup: {e}")
        # In production, you might want to fail here
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down EduAssist Backend API")
    
    try:
        await cache_manager.close()
        logger.info("Cache manager closed")
    except Exception as e:
        logger.error(f"Error closing cache manager: {e}")
    
    try:
        await close_db_connections()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
    
    logger.info("Application shutdown complete")


# Create FastAPI app with enhanced lifespan
app = FastAPI(
    title="EduAssist Backend API",
    description="Educational Management Platform API with Bulk Operations Support",
    version=settings.app_version,
    lifespan=lifespan
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Enhanced middleware with pool monitoring for bulk operations - FIXED"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Process-Time"] = str(process_time)
    
    # Add pool status for monitoring (optional, can be disabled in production) - FIXED
    if settings.environment == 'development':
        try:
            pool_status = await get_pool_status()
            # Check if pool_status contains error or proper structure
            if isinstance(pool_status, dict) and "error" not in pool_status:
                if "main_engine" in pool_status and "background_engine" in pool_status:
                    response.headers["X-Main-Pool-Active"] = str(pool_status["main_engine"]["checked_out"])
                    response.headers["X-Background-Pool-Active"] = str(pool_status["background_engine"]["checked_out"])
        except Exception as e:
            # Don't crash the request if pool status fails
            logger.debug(f"Failed to add pool status headers: {e}")
    
    # Log slow requests (especially important for bulk operations)
    if process_time > 5.0:  # Log requests taking longer than 5 seconds
        logger.warning(
            f"Slow request: {request.method} {request.url.path} - {process_time:.3f}s"
        )
    else:
        logger.info(f"{request.method} {request.url.path} - {process_time:.3f}s")
    
    return response


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if hasattr(settings, 'cors_origins') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)


# Include routers
app.include_router(health_router)
app.include_router(tenant_router)
app.include_router(school_authority_router)
app.include_router(teacher_router)
app.include_router(student_router)
app.include_router(class_router)
app.include_router(enrollment_router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "EduAssist Backend API",
        "version": settings.app_version,
        "features": [
            "Tenant Management",
            "School Authority Management",  # UPDATED FEATURES LIST
            "Connection Pooling",
            "Bulk Operations",  
            "Background Processing",
        ]
    }


# Health check with pool status
@app.get("/system/status")
async def system_status():
    """Enhanced system status including pool information - FIXED"""
    try:
        pool_status = await get_pool_status()
    except Exception as e:
        logger.error(f"Failed to get pool status for system status: {e}")
        pool_status = {"error": str(e)}
    
    return {
        "api_status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "database_pools": pool_status,
        "features": {
            "tenant_management": True,
            "school_authority_management": True,  # NEW FEATURE FLAG
            "bulk_operations": True,  # Set to True when implemented
            "background_tasks": True,  # Set to True when implemented
            "connection_pooling": True,
            "cache_manager": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",  # Use string import for better reloading
        host="0.0.0.0",
        port=8000,
        reload=(settings.environment == 'development'),
        log_level="info",
        access_log=True
    )
