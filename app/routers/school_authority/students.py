from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...models.tenant_specific.student import Student
from ...services.student_service import StudentService

router = APIRouter(prefix="/api/v1/school_authority/students", tags=["School Authority - Student Management"])

@router.get("/", response_model=dict)
async async def get_students(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tenant_id: Optional[UUID] = Query(None),
    grade_level: Optional[int] = Query(None),
    section: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated students with filtering"""
    service = StudentService(db)
    
    result = service.get_students_paginated(
        page=page,
        size=size,
        tenant_id=tenant_id,
        grade_level=grade_level,
        section=section
    )
    
    # Format student data
    formatted_students = [
        {
            "id": str(student.id),
            "tenant_id": str(student.tenant_id),
            "student_id": student.student_id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "email": student.email,
            "phone": student.phone,
            "grade_level": student.grade_level,
            "section": student.section,
            "admission_number": student.admission_number,
            "roll_number": student.roll_number,
            "academic_year": student.academic_year,
            "status": student.status,
            "parent_name": student.parent_info.get('primary_contact', {}).get('name') if student.parent_info else None,
            "parent_phone": student.parent_info.get('primary_contact', {}).get('phone') if student.parent_info else None,
            "created_at": student.created_at.isoformat(),
            "updated_at": student.updated_at.isoformat()
        }
        for student in result["items"]
    ]
    
    return {
        "items": formatted_students,
        "total": result["total"],
        "page": result["page"],
        "size": result["size"],
        "has_next": result["has_next"],
        "has_previous": result["has_previous"],
        "total_pages": result["total_pages"]
    }

@router.post("/", response_model=dict)
async async def create_student(
    student_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create new student"""
    service = StudentService(db)
    
    try:
        student = service.create(student_data)
        return {
            "id": str(student.id),
            "message": "Student created successfully",
            "student_id": student.student_id,
            "admission_number": student.admission_number
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{student_id}", response_model=dict)
async async def get_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific student with complete details"""
    service = StudentService(db)
    student = service.get(student_id)
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {
        "id": str(student.id),
        "tenant_id": str(student.tenant_id),
        "student_id": student.student_id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "email": student.email,
        "phone": student.phone,
        "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
        "address": student.address,
        "role": student.role,
        "status": student.status,
        "admission_number": student.admission_number,
        "roll_number": student.roll_number,
        "grade_level": student.grade_level,
        "section": student.section,
        "academic_year": student.academic_year,
        
        # Extended information from JSON fields
        "parent_info": student.parent_info,
        "health_medical_info": student.health_medical_info,
        "emergency_information": student.emergency_information,
        "behavioral_disciplinary": student.behavioral_disciplinary,
        "extended_academic_info": student.extended_academic_info,
        "enrollment_details": student.enrollment_details,
        "financial_info": student.financial_info,
        "extracurricular_social": student.extracurricular_social,
        "attendance_engagement": student.attendance_engagement,
        "additional_metadata": student.additional_metadata,
        
        "last_login": student.last_login.isoformat() if student.last_login else None,
        "created_at": student.created_at.isoformat(),
        "updated_at": student.updated_at.isoformat()
    }

@router.put("/{student_id}", response_model=dict)
async async def update_student(
    student_id: UUID,
    student_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update student information"""
    service = StudentService(db)
    student = service.update(student_id, student_data)
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {
        "id": str(student.id),
        "message": "Student updated successfully"
    }

@router.delete("/{student_id}")
async async def delete_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete student"""
    service = StudentService(db)
    success = service.soft_delete(student_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": "Student deactivated successfully"}

@router.get("/tenant/{tenant_id}")
async async def get_students_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all students for a specific school/tenant"""
    service = StudentService(db)
    students = service.get_by_tenant(tenant_id)
    
    return [
        {
            "id": str(student.id),
            "student_id": student.student_id,
            "name": f"{student.first_name} {student.last_name}",
            "email": student.email,
            "grade_level": student.grade_level,
            "section": student.section,
            "admission_number": student.admission_number,
            "status": student.status
        }
        for student in students
    ]

@router.get("/grade/{grade_level}")
async async def get_students_by_grade(
    grade_level: int,
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get students by grade level"""
    service = StudentService(db)
    students = service.get_students_by_grade(grade_level, tenant_id)
    
    return [
        {
            "id": str(student.id),
            "student_id": student.student_id,
            "name": f"{student.first_name} {student.last_name}",
            "email": student.email,
            "section": student.section,
            "roll_number": student.roll_number,
            "status": student.status
        }
        for student in students
    ]
