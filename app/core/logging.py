# app/core/logging.py
"""Logging configuration."""
import logging
import sys
from core.config import settings

def setup_logging():
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

logger = logging.getLogger(settings.APP_NAME)
setup_logging()
