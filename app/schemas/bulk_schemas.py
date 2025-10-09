# app/schemas/bulk_schemas.py
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class BulkUpdateResult(BaseModel):
    total_rows: int
    successful_updates: int
    failed_updates: int
    errors: List[Dict[str, Any]] = []
    processing_time_seconds: float
    operation_id: str

class TenantBulkUpdateRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    school_code: str = Field(..., description="Required for identifying the tenant")
    school_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    principal_name: Optional[str] = None
    annual_tuition: Optional[float] = None
    registration_fee: Optional[float] = None
    maximum_capacity: Optional[int] = None
    current_enrollment: Optional[int] = None
    total_students: Optional[int] = None
    total_teachers: Optional[int] = None

class BulkOperationStatus(BaseModel):
    operation_id: str
    status: str  # 'processing', 'completed', 'failed', 'completed_with_errors'
    progress_percentage: int = 0
    total_rows: Optional[int] = None
    processed_rows: Optional[int] = None
    successful_updates: Optional[int] = None
    failed_updates: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    errors: List[Dict[str, Any]] = []
    created_at: datetime
    completed_at: Optional[datetime] = None
