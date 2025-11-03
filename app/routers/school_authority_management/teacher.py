# app/routers/school_authority/teacher.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from datetime import datetime
from ...core.database import get_db
from ...models.tenant_specific.teacher import Teacher
from ...services.teacher_service import TeacherService

# Existing Pydantic Models
class TeacherCreate(BaseModel):
    tenant_id: UUID
    teacher_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    position: str
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    joining_date: Optional[datetime] = None
    role: Optional[str] = "teacher"
    status: Optional[str] = "active"
    qualification: Optional[str] = None
    experience_years: Optional[int] = 0
    teacher_details: Optional[dict] = None
    personal_info: Optional[dict] = None
    contact_info: Optional[dict] = None
    family_info: Optional[dict] = None
    qualifications: Optional[dict] = None
    employment: Optional[dict] = None
    academic_responsibilities: Optional[dict] = None
    timetable: Optional[dict] = None
    performance_evaluation: Optional[dict] = None

class TeacherUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[str] = None
    position: Optional[str] = None
    qualification: Optional[str] = None
    experience_years: Optional[int] = None
    teacher_details: Optional[dict] = None
    personal_info: Optional[dict] = None
    contact_info: Optional[dict] = None
    family_info: Optional[dict] = None
    qualifications: Optional[dict] = None
    employment: Optional[dict] = None
    academic_responsibilities: Optional[dict] = None
    timetable: Optional[dict] = None
    performance_evaluation: Optional[dict] = None
    status: Optional[str] = None

# NEW BULK OPERATION MODELS
class BulkTeacherImport(BaseModel):
    tenant_id: UUID
    teachers: List[dict]

class BulkStatusUpdate(BaseModel):
    tenant_id: UUID
    teacher_ids: List[str]
    new_status: str

class BulkSubjectAssignment(BaseModel):
    tenant_id: UUID
    assignments: List[dict]  # [{"teacher_id": "TCH001", "subjects": [{"subject": "Math", "grade": 10}]}]

class BulkSalaryUpdate(BaseModel):
    tenant_id: UUID
    salary_updates: List[dict]  # [{"teacher_id": "TCH001", "new_salary": 60000, "effective_date": "2024-01-01"}]

class BulkDeleteRequest(BaseModel):
    tenant_id: UUID
    teacher_ids: List[str]

router = APIRouter(prefix="/api/v1/school_authority/teachers", tags=["School Authority - Teacher Management"])

# EXISTING ENDPOINTS (unchanged)
@router.get("/", response_model=dict)
async def get_teachers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated teachers with filtering"""
    service = TeacherService(db)
    
    try:
        result = await service.get_teachers_paginated(
            page=page,
            size=size,
            tenant_id=tenant_id
        )
        
        formatted_teachers = [
            {
                "id": str(teacher.id),
                "tenant_id": str(teacher.tenant_id),
                "teacher_id": teacher.teacher_id,
                
                # Use individual fields first, fallback to JSON
                "first_name": teacher.first_name or (teacher.personal_info.get('basic_details', {}).get('first_name', '') if teacher.personal_info else ''),
                "last_name": teacher.last_name or (teacher.personal_info.get('basic_details', {}).get('last_name', '') if teacher.personal_info else ''),
                "email": teacher.email or (teacher.personal_info.get('contact_info', {}).get('primary_email', '') if teacher.personal_info else ''),
                "phone": teacher.phone or (teacher.personal_info.get('contact_info', {}).get('primary_phone', '') if teacher.personal_info else ''),
                "gender": teacher.gender,
                
                # Employment info
                "position": teacher.position or (teacher.employment.get('job_information', {}).get('current_position', '') if teacher.employment else ''),
                "department": (teacher.teacher_details.get('department', '') if teacher.teacher_details else '') or (teacher.employment.get('job_information', {}).get('department', '') if teacher.employment else ''),
                "joining_date": (teacher.joining_date.isoformat() if teacher.joining_date else '') or (teacher.employment.get('job_information', {}).get('joining_date', '') if teacher.employment else ''),
                
                # Teaching subjects
                "subjects": [assignment.get('subject', '') for assignment in (teacher.academic_responsibilities.get('teaching_assignments', []) if teacher.academic_responsibilities else [])],
                
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=dict)
async def create_teacher(
    teacher_data: TeacherCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new teacher"""
    service = TeacherService(db)
    
    teacher_dict = teacher_data.model_dump()
    teacher = await service.create(teacher_dict)
    
    return {
        "id": str(teacher.id),
        "message": "Teacher created successfully",
        "teacher_id": teacher.teacher_id
    }

@router.get("/{teacher_id}", response_model=dict)
async def get_teacher(
    teacher_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific teacher with complete details"""
    service = TeacherService(db)
    teacher = await service.get(teacher_id)
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    return {
        "id": str(teacher.id),
        "tenant_id": str(teacher.tenant_id),
        "teacher_id": teacher.teacher_id,
        "personal_info": teacher.personal_info,
        "contact_info": teacher.contact_info,
        "family_info": teacher.family_info,
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
async def update_teacher(
    teacher_id: UUID,
    teacher_data: TeacherUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update teacher information"""
    service = TeacherService(db)
    
    update_dict = teacher_data.model_dump(exclude_unset=True)
    teacher = await service.update(teacher_id, update_dict)
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    return {
        "id": str(teacher.id),
        "message": "Teacher updated successfully"
    }

@router.delete("/{teacher_id}")
async def delete_teacher(
    teacher_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete teacher"""
    service = TeacherService(db)
    success = await service.soft_delete(teacher_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    return {"message": "Teacher deactivated successfully"}

@router.get("/tenant/{tenant_id}")
async def get_teachers_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all teachers for a specific school/tenant"""
    service = TeacherService(db)
    teachers = await service.get_by_tenant(tenant_id)
    
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
async def get_teachers_by_subject(
    subject: str,
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get teachers who teach a specific subject"""
    service = TeacherService(db)
    teachers = await service.get_teachers_by_subject(subject, tenant_id)
    
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

# NEW BULK OPERATION ENDPOINTS

@router.post("/bulk/import", response_model=dict)
async def bulk_import_teachers(
    import_data: BulkTeacherImport,
    db: AsyncSession = Depends(get_db)
):
    """Bulk import teachers from CSV/JSON data"""
    service = TeacherService(db)
    
    result = await service.bulk_import_teachers(
        teachers_data=import_data.teachers,
        tenant_id=import_data.tenant_id
    )
    
    return {
        "message": f"Bulk import completed. {result['successful_imports']} teachers imported successfully",
        **result
    }

@router.post("/bulk/update-status", response_model=dict)
async def bulk_update_status(
    status_data: BulkStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update teacher status"""
    service = TeacherService(db)
    
    result = await service.bulk_update_status(
        teacher_ids=status_data.teacher_ids,
        new_status=status_data.new_status,
        tenant_id=status_data.tenant_id
    )
    
    return {
        "message": f"Status update completed. {result['updated_teachers']} teachers updated to '{result['new_status']}'",
        **result
    }

@router.post("/bulk/assign-subjects", response_model=dict)
async def bulk_assign_subjects(
    assignment_data: BulkSubjectAssignment,
    db: AsyncSession = Depends(get_db)
):
    """Bulk assign subjects to teachers"""
    service = TeacherService(db)
    
    result = await service.bulk_assign_subjects(
        subject_assignments=assignment_data.assignments,
        tenant_id=assignment_data.tenant_id
    )
    
    return {
        "message": f"Subject assignment completed. {result['updated_teachers']} teachers updated",
        **result
    }

@router.post("/bulk/update-salaries", response_model=dict)
async def bulk_update_salaries(
    salary_data: BulkSalaryUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update teacher salaries"""
    service = TeacherService(db)
    
    result = await service.bulk_salary_update(
        salary_updates=salary_data.salary_updates,
        tenant_id=salary_data.tenant_id
    )
    
    return {
        "message": f"Salary update completed. {result['updated_teachers']} teachers updated",
        **result
    }

@router.post("/bulk/delete", response_model=dict)
async def bulk_delete_teachers(
    delete_data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk soft delete teachers"""
    service = TeacherService(db)
    
    result = await service.bulk_soft_delete(
        teacher_ids=delete_data.teacher_ids,
        tenant_id=delete_data.tenant_id
    )
    
    return {
        "message": f"Bulk delete completed. {result['deleted_teachers']} teachers deactivated",
        **result
    }

@router.get("/statistics/{tenant_id}", response_model=dict)
async def get_teacher_statistics(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive teacher statistics for a school"""
    service = TeacherService(db)
    
    stats = await service.get_teacher_statistics(tenant_id)
    
    return {
        "message": "Teacher statistics retrieved successfully",
        **stats
    }
