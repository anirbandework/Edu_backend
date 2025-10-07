# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time

from .core.config import settings
from .core.database import engine
from .core.cache import cache_manager
# Remove this problematic import
# from .core.db_warmup import warm_up_connections
from .routers.health import router as health_router
from .routers.tenant import router as tenant_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting app")
    
    # Initialize cache first
    await cache_manager.initialize()
    logger.info("Cache initialized")
    
    # Remove the database warmup that's hanging
    # await warm_up_connections()
    # logger.info("Database connections warmed up")
    
    yield
    
    logger.info("Shutting down app")
    await cache_manager.close()
    await engine.dispose()
    logger.info("Shutdown complete")

# Rest of your code remains the same...
app = FastAPI(lifespan=lifespan)

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

app.include_router(health_router)
app.include_router(tenant_router)

@app.get("/")
async def root():
    return {"message": "EduAssist Backend API", "version": settings.app_version}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
