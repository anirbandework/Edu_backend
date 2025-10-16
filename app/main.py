from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time

from .core.config import settings
from .core.database import engine
from .core.cache import cache_manager

# Import all routers
from .routers import health, tenants, school_authorities
from .routers.school_authority import (
    teachers, students, classes, attendance, timetable, 
    fee_management, grades, notifications, teacher_notifications, ai_prediction
)
from .routers.student_portal import notifications as student_notifications
from .routers.doubt_chat import student_chat, teacher_chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EduAssist API Gateway")
    
    # Initialize cache
    await cache_manager.initialize()
    logger.info("Cache initialized")
    
    yield
    
    logger.info("Shutting down EduAssist API Gateway")
    await cache_manager.close()
    await engine.dispose()
    logger.info("Shutdown complete")

app = FastAPI(
    title="EduAssist API Gateway - AI-Powered School Management",
    description="Complete Multi-tenant School Management System with AI Predictions and Caching",
    version="4.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {process_time:.3f}s")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Include all routers
app.include_router(health.router)
app.include_router(tenants.router)
app.include_router(school_authorities.router)
app.include_router(teachers.router)
app.include_router(students.router)
app.include_router(classes.router)
app.include_router(attendance.router)
app.include_router(timetable.router)
app.include_router(fee_management.router)
app.include_router(grades.router)
app.include_router(notifications.router)
app.include_router(teacher_notifications.router)
app.include_router(student_notifications.router)
app.include_router(student_chat.router)
app.include_router(teacher_chat.router)
app.include_router(ai_prediction.router)

@app.get("/")
async def root():
    return {
        "message": "EduAssist API Gateway v4.0 - AI-Powered with Redis Caching",
        "version": "4.0.0",
        "features": ["Multi-tenant", "AI Predictions", "Real-time Chat", "Redis Caching", "Async Operations"],
        "status": "active"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
