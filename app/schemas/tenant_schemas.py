#   app/schemas/tenant_schemas.py
"""Pydantic schemas for Tenant (School) entity."""
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr

class TenantBase(BaseModel):
    school_name: str
    address: str
    phone: str
    email: EmailStr
    principal_name: str
    is_active: Optional[bool] = True

    annual_tuition: float
    registration_fee: float

    total_students: Optional[int] = 0
    total_teachers: Optional[int] = 0
    total_staff: Optional[int] = 0
    maximum_capacity: int
    current_enrollment: Optional[int] = 0

    school_type: Optional[str] = "K-12"
    grade_levels: List[str]
    academic_year_start: Optional[datetime]
    academic_year_end: Optional[datetime]
    established_year: Optional[int]
    accreditation: Optional[str]
    language_of_instruction: Optional[str] = "English"

class TenantCreate(TenantBase):
    pass  # school_code not needed for creation

class TenantUpdate(TenantBase):
    school_code: Optional[str] = None  # Optional for updates

class TenantInDBBase(TenantBase):
    school_code: str  # Auto-generated, so always present in DB responses
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Tenant(TenantInDBBase):
    pass
