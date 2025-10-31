# app/schemas/teacher_assignment_schemas.py
from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class TeacherAssignmentBase(BaseModel):
    subject_name: str = Field(..., min_length=1, max_length=100)
    academic_year: str = Field(..., min_length=1, max_length=10)
    is_primary_teacher: Optional[bool] = Field(default=False)
    is_active: Optional[bool] = Field(default=True)

class TeacherAssignmentCreate(TeacherAssignmentBase):
    teacher_id: UUID
    class_id: UUID

class TeacherAssignmentUpdate(BaseModel):
    subject_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    academic_year: Optional[str] = Field(default=None, min_length=1, max_length=10)
    is_primary_teacher: Optional[bool] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)

class TeacherAssignment(TeacherAssignmentBase):
    id: UUID
    tenant_id: UUID
    teacher_id: UUID
    class_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True