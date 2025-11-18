from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging
from typing import Union

logger = logging.getLogger(__name__)

class AssessmentException(Exception):
    """Base exception for assessment system"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationException(AssessmentException):
    """Validation error exception"""
    def __init__(self, message: str):
        super().__init__(message, 400)

class NotFoundError(AssessmentException):
    """Resource not found exception"""
    def __init__(self, resource: str, id: str = None):
        message = f"{resource} not found"
        if id:
            message += f" with id: {id}"
        super().__init__(message, 404)

class PermissionError(AssessmentException):
    """Permission denied exception"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, 403)

async def assessment_exception_handler(request: Request, exc: AssessmentException):
    """Handle custom assessment exceptions"""
    logger.error(f"Assessment error: {exc.message} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "type": exc.__class__.__name__}
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {str(exc)} - Path: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "type": "InternalError"}
    )