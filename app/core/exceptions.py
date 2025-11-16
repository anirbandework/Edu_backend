# app/core/exceptions.py
"""Custom exceptions for the EduAssist application."""
from fastapi import HTTPException
from typing import Any, Dict, Optional


class EduAssistException(HTTPException):
    """Base exception for EduAssist application."""
    def __init__(
        self, 
        status_code: int, 
        detail: str, 
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class TenantNotFound(EduAssistException):
    """Exception raised when tenant is not found."""
    def __init__(self):
        super().__init__(
            status_code=404,
            detail="School not found"
        )


class DuplicateTenantError(EduAssistException):
    """Exception raised when duplicate tenant data is found."""
    def __init__(self, field: str, value: str):
        super().__init__(
            status_code=409,
            detail={
                "error": f"Duplicate {field}",
                "message": f"A school with this {field} already exists",
                "field": field,
                "value": value
            }
        )


class BulkOperationError(EduAssistException):
    """Exception raised during bulk operations."""
    def __init__(self, message: str):
        super().__init__(
            status_code=400,
            detail={
                "error": "Bulk Operation Failed",
                "message": message
            }
        )


class ValidationError(EduAssistException):
    """Exception raised for validation errors."""
    def __init__(self, message: str, field: Optional[str] = None):
        detail = {"error": "Validation Error", "message": message}
        if field:
            detail["field"] = field
        super().__init__(status_code=422, detail=detail)


class DatabaseError(EduAssistException):
    """Exception raised for database errors."""
    def __init__(self, message: str):
        super().__init__(
            status_code=500,
            detail={
                "error": "Database Error", 
                "message": message
            }
        )
