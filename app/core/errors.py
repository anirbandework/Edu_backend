# app/core/errors.py
from fastapi import HTTPException

class EduAssistException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

# Example common errors
def not_found_error(message: str = "Resource not found"):
    return EduAssistException(status_code=404, detail=message)

def bad_request_error(message: str = "Bad request"):
    return EduAssistException(status_code=400, detail=message)
