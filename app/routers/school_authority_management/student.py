# app/routers/school_authority/student.py
from typing import List, Optional
from uuid import UUID
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from datetime import datetime
from ...core.database import get_db
from ...utils.pagination import Paginator, PaginationParams
from ...utils.cache_decorators import cache_paginated_response
from ...models.tenant_specific.student import Student
from ...services.student_service import StudentService

# Pydantic Models
class StudentCreate(BaseModel):
    tenant_id: UUID
    student_id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: datetime
    address: str
    admission_number: str
    roll_number: Optional[str] = None
    grade_level: int
    section: Optional[str] = None
    academic_year: str
    parent_info: Optional[dict] = None
    health_medical_info: Optional[dict] = None
    emergency_information: Optional[dict] = None
    behavioral_disciplinary: Optional[dict] = None
    extended_academic_info: Optional[dict] = None
    enrollment_details: Optional[dict] = None
    financial_info: Optional[dict] = None
    extracurricular_social: Optional[dict] = None
    attendance_engagement: Optional[dict] = None
    additional_metadata: Optional[dict] = None

class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    roll_number: Optional[str] = None
    grade_level: Optional[int] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None
    status: Optional[str] = None
    parent_info: Optional[dict] = None
    health_medical_info: Optional[dict] = None
    emergency_information: Optional[dict] = None
    behavioral_disciplinary: Optional[dict] = None
    extended_academic_info: Optional[dict] = None
    enrollment_details: Optional[dict] = None
    financial_info: Optional[dict] = None
    extracurricular_social: Optional[dict] = None
    attendance_engagement: Optional[dict] = None
    additional_metadata: Optional[dict] = None

# NEW BULK OPERATION MODELS
class BulkStudentImport(BaseModel):
    tenant_id: UUID
    students: List[dict]  # List of student data dictionaries

class BulkGradeUpdate(BaseModel):
    tenant_id: UUID
    grade_updates: List[dict]  # [{"student_id": "STU001", "new_grade": 11}]

class BulkStatusUpdate(BaseModel):
    tenant_id: UUID
    student_ids: List[str]
    new_status: str

class BulkSectionUpdate(BaseModel):
    tenant_id: UUID
    section_updates: List[dict]  # [{"student_id": "STU001", "new_section": "B"}]

class BulkDeleteRequest(BaseModel):
    tenant_id: UUID
    student_ids: List[str]

class BulkPromotionRequest(BaseModel):
    tenant_id: UUID
    current_grade: int
    academic_year: str

router = APIRouter(prefix="/api/v1/school_authority/students", tags=["School Authority - Student Management"])

# EXISTING ENDPOINTS (unchanged)
@router.get("/", response_model=dict)
@cache_paginated_response("students", expire=timedelta(minutes=8))
async def get_students(
    pagination: PaginationParams = Depends(Paginator.get_pagination_params),
    tenant_id: Optional[UUID] = Query(None),
    grade_level: Optional[int] = Query(None),
    section: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated students with filtering"""
    service = StudentService(db)
    
    try:
        # Build filters
        filters = {}
        if tenant_id:
            filters["tenant_id"] = tenant_id
        if grade_level:
            filters["grade_level"] = grade_level
        if section:
            filters["section"] = section
            
        result = await service.get_paginated(
            page=pagination.page,
            size=pagination.size,
            **filters
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
        
        # Update response with formatted items
        result["items"] = formatted_students
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=dict)
async def create_student(
    student_data: StudentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new student"""
    service = StudentService(db)
    
    student_dict = student_data.model_dump()
    student = await service.create(student_dict)
    
    return {
        "id": str(student.id),
        "message": "Student created successfully",
        "student_id": student.student_id,
        "admission_number": student.admission_number
    }

@router.get("/{student_id}", response_model=dict)
async def get_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific student with complete details"""
    service = StudentService(db)
    student = await service.get(student_id)
    
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
async def update_student(
    student_id: UUID,
    student_data: StudentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update student information"""
    service = StudentService(db)
    
    update_dict = student_data.model_dump(exclude_unset=True)
    student = await service.update(student_id, update_dict)
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {
        "id": str(student.id),
        "message": "Student updated successfully"
    }

@router.delete("/{student_id}")
async def delete_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete student"""
    service = StudentService(db)
    success = await service.soft_delete(student_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": "Student deactivated successfully"}

@router.get("/tenant/{tenant_id}")
async def get_students_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all students for a specific school/tenant"""
    service = StudentService(db)
    students = await service.get_by_tenant(tenant_id)
    
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
async def get_students_by_grade(
    grade_level: int,
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get students by grade level"""
    service = StudentService(db)
    students = await service.get_students_by_grade(grade_level, tenant_id)
    
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

# NEW BULK OPERATION ENDPOINTS

@router.post("/bulk/import", response_model=dict)
async def bulk_import_students(
    import_data: BulkStudentImport,
    db: AsyncSession = Depends(get_db)
):
    """Bulk import students from CSV/JSON data"""
    service = StudentService(db)
    
    result = await service.bulk_import_students(
        students_data=import_data.students,
        tenant_id=import_data.tenant_id
    )
    
    return {
        "message": f"Bulk import completed. {result['successful_imports']} students imported successfully",
        **result
    }

@router.post("/bulk/update-grades", response_model=dict)
async def bulk_update_grades(
    grade_data: BulkGradeUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update student grades"""
    service = StudentService(db)
    
    result = await service.bulk_update_grades(
        grade_updates=grade_data.grade_updates,
        tenant_id=grade_data.tenant_id
    )
    
    return {
        "message": f"Bulk grade update completed. {result['updated_students']} students updated",
        **result
    }

@router.post("/bulk/promote", response_model=dict)
async def bulk_promote_students(
    promotion_data: BulkPromotionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Promote all students from current grade to next grade"""
    service = StudentService(db)
    
    result = await service.bulk_promote_students(
        current_grade=promotion_data.current_grade,
        tenant_id=promotion_data.tenant_id,
        academic_year=promotion_data.academic_year
    )
    
    return {
        "message": f"Promotion completed. {result['promoted_students']} students promoted from grade {result['from_grade']} to {result['to_grade']}",
        **result
    }

@router.post("/bulk/update-status", response_model=dict)
async def bulk_update_status(
    status_data: BulkStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update student status"""
    service = StudentService(db)
    
    result = await service.bulk_update_status(
        student_ids=status_data.student_ids,
        new_status=status_data.new_status,
        tenant_id=status_data.tenant_id
    )
    
    return {
        "message": f"Status update completed. {result['updated_students']} students updated to '{result['new_status']}'",
        **result
    }

@router.post("/bulk/update-sections", response_model=dict)
async def bulk_update_sections(
    section_data: BulkSectionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update student sections"""
    service = StudentService(db)
    
    result = await service.bulk_update_sections(
        section_updates=section_data.section_updates,
        tenant_id=section_data.tenant_id
    )
    
    return {
        "message": f"Section update completed. {result['updated_students']} students updated",
        **result
    }

@router.post("/bulk/delete", response_model=dict)
async def bulk_delete_students(
    delete_data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk soft delete students"""
    service = StudentService(db)
    
    result = await service.bulk_soft_delete(
        student_ids=delete_data.student_ids,
        tenant_id=delete_data.tenant_id
    )
    
    return {
        "message": f"Bulk delete completed. {result['deleted_students']} students deactivated",
        **result
    }

@router.get("/statistics/{tenant_id}", response_model=dict)
async def get_student_statistics(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive student statistics for a school"""
    service = StudentService(db)
    
    stats = await service.get_student_statistics(tenant_id)
    
    return {
        "message": "Student statistics retrieved successfully",
        **stats
    }

# ADDITIONAL UTILITY ENDPOINTS

@router.get("/export/{tenant_id}")
async def export_students(
    tenant_id: UUID,
    format: str = Query("json", enum=["json", "csv"]),
    grade_level: Optional[int] = Query(None),
    section: Optional[str] = Query(None),
    status: Optional[str] = Query("active"),
    db: AsyncSession = Depends(get_db)
):
    """Export student data in JSON or CSV format"""
    service = StudentService(db)
    
    try:
        # Get filtered students
        filters = {"tenant_id": tenant_id}
        if grade_level:
            filters["grade_level"] = grade_level
        if section:
            filters["section"] = section
        if status:
            filters["status"] = status
        
        result = await service.get_paginated(page=1, size=10000, **filters)
        students = result["items"]
        
        if format == "csv":
            # Return CSV format headers for frontend processing
            return {
                "format": "csv",
                "headers": [
                    "student_id", "first_name", "last_name", "email", "phone",
                    "grade_level", "section", "admission_number", "academic_year", "status"
                ],
                "data": [
                    [
                        student.student_id, student.first_name, student.last_name,
                        student.email or "", student.phone or "",
                        student.grade_level, student.section or "",
                        student.admission_number, student.academic_year, student.status
                    ]
                    for student in students
                ],
                "total_exported": len(students)
            }
        else:
            # JSON format
            return {
                "format": "json",
                "students": [
                    {
                        "id": str(student.id),
                        "student_id": student.student_id,
                        "first_name": student.first_name,
                        "last_name": student.last_name,
                        "email": student.email,
                        "phone": student.phone,
                        "grade_level": student.grade_level,
                        "section": student.section,
                        "admission_number": student.admission_number,
                        "academic_year": student.academic_year,
                        "status": student.status,
                        "created_at": student.created_at.isoformat()
                    }
                    for student in students
                ],
                "total_exported": len(students)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
