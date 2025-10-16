from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...models.tenant_specific.teacher import Teacher
from ...services.teacher_service import TeacherService

router = APIRouter(prefix="/api/v1/school_authority/teachers", tags=["School Authority - Teacher Management"])

@router.get("/", response_model=dict)
async async def get_teachers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated teachers with filtering"""
    service = TeacherService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    
    result = service.get_teachers_paginated(
        page=page,
        size=size,
        tenant_id=tenant_id
    )
    
    formatted_teachers = [
        {
            "id": str(teacher.id),
            "tenant_id": str(teacher.tenant_id),
            "teacher_id": teacher.teacher_id,
            
            # Extract basic info from JSON
            "first_name": teacher.personal_info.get('basic_details', {}).get('first_name', '') if teacher.personal_info else '',
            "last_name": teacher.personal_info.get('basic_details', {}).get('last_name', '') if teacher.personal_info else '',
            "title": teacher.personal_info.get('basic_details', {}).get('title', '') if teacher.personal_info else '',
            "email": teacher.personal_info.get('contact_info', {}).get('primary_email', '') if teacher.personal_info else '',
            "phone": teacher.personal_info.get('contact_info', {}).get('primary_phone', '') if teacher.personal_info else '',
            
            # Employment info
            "position": teacher.employment.get('job_information', {}).get('current_position', '') if teacher.employment else '',
            "department": teacher.employment.get('job_information', {}).get('department', '') if teacher.employment else '',
            "joining_date": teacher.employment.get('job_information', {}).get('joining_date', '') if teacher.employment else '',
            
            # Teaching subjects
            "subjects": [assignment.get('subject', '') for assignment in teacher.academic_responsibilities.get('teaching_assignments', []) if teacher.academic_responsibilities] if teacher.academic_responsibilities else [],
            
            "status": teacher.status,
            "last_login": teacher.last_login.isoformat() if teacher.last_login else None,
            "created_at": teacher.created_at.isoformat(),
            "updated_at": teacher.updated_at.isoformat()
        }
        for teacher in result["items"]
    ]
    
    return {
        "items": formatted_teachers,
        "total": result["total"],
        "page": result["page"],
        "size": result["size"],
        "has_next": result["has_next"],
        "has_previous": result["has_previous"],
        "total_pages": result["total_pages"]
    }

@router.post("/", response_model=dict)
async async def create_teacher(
    teacher_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create new teacher"""
    service = TeacherService(db)
    
    try:
        teacher = service.create(teacher_data)
        return {
            "id": str(teacher.id),
            "message": "Teacher created successfully",
            "teacher_id": teacher.teacher_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{teacher_id}", response_model=dict)
async async def get_teacher(
    teacher_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific teacher with complete details"""
    service = TeacherService(db)
    teacher = service.get(teacher_id)
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    return {
        "id": str(teacher.id),
        "tenant_id": str(teacher.tenant_id),
        "teacher_id": teacher.teacher_id,
        "personal_info": teacher.personal_info,
        "qualifications": teacher.qualifications,
        "employment": teacher.employment,
        "academic_responsibilities": teacher.academic_responsibilities,
        "timetable": teacher.timetable,
        "performance_evaluation": teacher.performance_evaluation,
        "status": teacher.status,
        "last_login": teacher.last_login.isoformat() if teacher.last_login else None,
        "created_at": teacher.created_at.isoformat(),
        "updated_at": teacher.updated_at.isoformat()
    }

@router.put("/{teacher_id}", response_model=dict)
async async def update_teacher(
    teacher_id: UUID,
    teacher_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update teacher information"""
    service = TeacherService(db)
    teacher = service.update(teacher_id, teacher_data)
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    return {
        "id": str(teacher.id),
        "message": "Teacher updated successfully"
    }

@router.delete("/{teacher_id}")
async async def delete_teacher(
    teacher_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete teacher"""
    service = TeacherService(db)
    success = service.soft_delete(teacher_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    return {"message": "Teacher deactivated successfully"}

@router.get("/tenant/{tenant_id}")
async async def get_teachers_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all teachers for a specific school/tenant"""
    service = TeacherService(db)
    teachers = service.get_teachers_by_tenant_cached(tenant_id)
    
    return [
        {
            "id": str(teacher.id),
            "teacher_id": teacher.teacher_id,
            "name": f"{teacher.personal_info.get('basic_details', {}).get('first_name', '')} {teacher.personal_info.get('basic_details', {}).get('last_name', '')}" if teacher.personal_info else "",
            "email": teacher.personal_info.get('contact_info', {}).get('primary_email', '') if teacher.personal_info else '',
            "position": teacher.employment.get('job_information', {}).get('current_position', '') if teacher.employment else '',
            "department": teacher.employment.get('job_information', {}).get('department', '') if teacher.employment else '',
            "status": teacher.status
        }
        for teacher in teachers
    ]

@router.get("/subject/{subject}")
async async def get_teachers_by_subject(
    subject: str,
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get teachers who teach a specific subject"""
    service = TeacherService(db)
    teachers = service.get_teachers_by_subject_cached(subject, tenant_id)
    
    return [
        {
            "id": str(teacher.id),
            "teacher_id": teacher.teacher_id,
            "name": f"{teacher.personal_info.get('basic_details', {}).get('first_name', '')} {teacher.personal_info.get('basic_details', {}).get('last_name', '')}" if teacher.personal_info else "",
            "email": teacher.personal_info.get('contact_info', {}).get('primary_email', '') if teacher.personal_info else '',
            "department": teacher.employment.get('job_information', {}).get('department', '') if teacher.employment else '',
            "subject": subject,
            "status": teacher.status
        }
        for teacher in teachers
    ]
