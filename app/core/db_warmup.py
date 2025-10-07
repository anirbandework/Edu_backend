"""Database connection warmup for Aurora cold start mitigation."""
import asyncio
import logging
from sqlalchemy import text
from .database import engine

logger = logging.getLogger(__name__)

async def warm_up_connections():
    """Pre-warm database connections to reduce cold start latency"""
    try:
        # Create and test multiple connections
        tasks = []
        for i in range(3):  # Warm up 3 connections
            tasks.append(warm_connection(f"warmup-{i}"))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Database connections warmed up successfully")
    except Exception as e:
        logger.warning(f"Connection warmup failed: {e}")

async def warm_connection(connection_name: str):
    """Warm up individual connection"""
    async with engine.connect() as conn:
        # Execute lightweight query to establish connection
        await conn.execute(text("SELECT 1 as warmup"))
        logger.info(f"Connection {connection_name} warmed up")
