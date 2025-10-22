# app/routers/school_authority/enrollment.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime
from datetime import timedelta
from ...utils.pagination import Paginator, PaginationParams
from ...utils.cache_decorators import cache_paginated_response
from ...core.database import get_db
from ...models.tenant_specific.enrollment import Enrollment
from ...services.enrollment_service import EnrollmentService

# Existing Pydantic Models
class EnrollmentCreate(BaseModel):
    student_id: UUID
    class_id: UUID
    academic_year: str
    enrollment_date: datetime = datetime.utcnow()
    status: str = "active"

class EnrollmentUpdate(BaseModel):
    academic_year: Optional[str] = None
    enrollment_date: Optional[datetime] = None
    status: Optional[str] = None

class BulkEnrollmentCreate(BaseModel):
    class_id: UUID
    student_ids: List[UUID]
    academic_year: str

class StatusUpdate(BaseModel):
    status: str

# NEW BULK OPERATION MODELS
class BulkEnrollmentImport(BaseModel):
    enrollments: List[dict]  # [{"student_id": UUID, "class_id": UUID, "academic_year": str}]

class BulkStatusUpdate(BaseModel):
    enrollment_ids: List[UUID]
    new_status: str

class BulkTransferStudents(BaseModel):
    student_ids: List[UUID]
    from_class_id: UUID
    to_class_id: UUID
    academic_year: str

class AcademicYearRollover(BaseModel):
    current_year: str
    new_year: str
    tenant_id: UUID

class BulkDeleteRequest(BaseModel):
    enrollment_ids: List[UUID]

class BulkEnrollByGrade(BaseModel):
    grade_level: int
    target_class_ids: List[UUID]  # Classes to distribute students across
    academic_year: str
    tenant_id: UUID

class BulkWithdrawStudents(BaseModel):
    student_ids: List[UUID]
    academic_year: str
    withdrawal_reason: Optional[str] = "Withdrawn"

router = APIRouter(prefix="/api/v1/school_authority/enrollments", tags=["School Authority - Enrollment Management"])

# EXISTING ENDPOINTS (unchanged)
@router.get("/", response_model=dict)
async def get_enrollments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    student_id: Optional[UUID] = Query(None),
    class_id: Optional[UUID] = Query(None),
    academic_year: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated enrollments with filtering"""
    service = EnrollmentService(db)
    
    try:
        result = await service.get_enrollments_paginated(
            page=page,
            size=size,
            student_id=student_id,
            class_id=class_id,
            academic_year=academic_year,
            status=status
        )
        
        formatted_enrollments = [
            {
                "id": str(enrollment.id),
                "student_id": str(enrollment.student_id),
                "class_id": str(enrollment.class_id),
                "academic_year": enrollment.academic_year,
                "enrollment_date": enrollment.enrollment_date.isoformat(),
                "status": enrollment.status,
                "created_at": enrollment.created_at.isoformat(),
                "updated_at": enrollment.updated_at.isoformat()
            }
            for enrollment in result["items"]
        ]
        
        return {
            "items": formatted_enrollments,
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
async def create_enrollment(
    enrollment_data: EnrollmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new enrollment"""
    service = EnrollmentService(db)
    
    enrollment_dict = enrollment_data.model_dump()
    enrollment = await service.create(enrollment_dict)
    
    return {
        "id": str(enrollment.id),
        "message": "Student enrolled successfully",
        "student_id": str(enrollment.student_id),
        "class_id": str(enrollment.class_id),
        "academic_year": enrollment.academic_year
    }

@router.post("/bulk", response_model=dict)
async def bulk_enroll_students(
    bulk_data: BulkEnrollmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk enroll multiple students in a class"""
    service = EnrollmentService(db)
    
    result = await service.bulk_enroll_students(
        class_id=bulk_data.class_id,
        student_ids=bulk_data.student_ids,
        academic_year=bulk_data.academic_year
    )
    
    return {
        "message": f"Bulk enrollment completed. {result['successful_enrollments']} successful, {result['failed_enrollments']} failed",
        **result
    }

# NEW ADVANCED BULK OPERATION ENDPOINTS

@router.post("/bulk/import", response_model=dict)
async def bulk_import_enrollments(
    import_data: BulkEnrollmentImport,
    db: AsyncSession = Depends(get_db)
):
    """Bulk import enrollments from CSV/JSON data"""
    service = EnrollmentService(db)
    
    result = await service.bulk_import_enrollments(
        enrollments_data=import_data.enrollments
    )
    
    return {
        "message": f"Bulk import completed. {result['successful_enrollments']} enrollments imported successfully",
        **result
    }

@router.post("/bulk/update-status", response_model=dict)
async def bulk_update_enrollment_status(
    status_data: BulkStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update enrollment status"""
    service = EnrollmentService(db)
    
    result = await service.bulk_update_enrollment_status(
        enrollment_ids=status_data.enrollment_ids,
        new_status=status_data.new_status
    )
    
    return {
        "message": f"Status update completed. {result['updated_enrollments']} enrollments updated to '{result['new_status']}'",
        **result
    }

@router.post("/bulk/transfer", response_model=dict)
async def bulk_transfer_students(
    transfer_data: BulkTransferStudents,
    db: AsyncSession = Depends(get_db)
):
    """Bulk transfer students between classes"""
    service = EnrollmentService(db)
    
    result = await service.bulk_transfer_students(
        student_ids=transfer_data.student_ids,
        from_class_id=transfer_data.from_class_id,
        to_class_id=transfer_data.to_class_id,
        academic_year=transfer_data.academic_year
    )
    
    return {
        "message": f"Transfer completed. {result['transferred_students']} students transferred from {result['from_class_id']} to {result['to_class_id']}",
        **result
    }

@router.post("/bulk/academic-year-rollover", response_model=dict)
async def academic_year_rollover(
    rollover_data: AcademicYearRollover,
    db: AsyncSession = Depends(get_db)
):
    """Promote all students to next academic year"""
    service = EnrollmentService(db)
    
    result = await service.academic_year_rollover(
        current_year=rollover_data.current_year,
        new_year=rollover_data.new_year,
        tenant_id=rollover_data.tenant_id
    )
    
    return {
        "message": f"Academic year rollover completed. {result['promoted_students']} students promoted from {result['previous_academic_year']} to {result['new_academic_year']}",
        **result
    }

@router.post("/bulk/enroll-by-grade", response_model=dict)
async def bulk_enroll_by_grade(
    grade_data: BulkEnrollByGrade,
    db: AsyncSession = Depends(get_db)
):
    """Bulk enroll students by grade level across multiple classes"""
    service = EnrollmentService(db)
    
    result = await service.bulk_enroll_by_grade(
        grade_level=grade_data.grade_level,
        target_class_ids=grade_data.target_class_ids,
        academic_year=grade_data.academic_year,
        tenant_id=grade_data.tenant_id
    )
    
    return {
        "message": f"Grade-based enrollment completed. {result['enrolled_students']} students from grade {grade_data.grade_level} enrolled across {len(grade_data.target_class_ids)} classes",
        **result
    }

@router.post("/bulk/withdraw", response_model=dict)
async def bulk_withdraw_students(
    withdraw_data: BulkWithdrawStudents,
    db: AsyncSession = Depends(get_db)
):
    """Bulk withdraw students from all enrollments"""
    service = EnrollmentService(db)
    
    result = await service.bulk_withdraw_students(
        student_ids=withdraw_data.student_ids,
        academic_year=withdraw_data.academic_year,
        withdrawal_reason=withdraw_data.withdrawal_reason
    )
    
    return {
        "message": f"Withdrawal completed. {result['withdrawn_students']} students withdrawn from all classes",
        **result
    }

@router.post("/bulk/auto-assign", response_model=dict)
async def bulk_auto_assign_enrollments(
    tenant_id: UUID,
    academic_year: str,
    grade_level: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Auto-assign unenrolled students to available classes"""
    service = EnrollmentService(db)
    
    result = await service.bulk_auto_assign_enrollments(
        tenant_id=tenant_id,
        academic_year=academic_year,
        grade_level=grade_level
    )
    
    return {
        "message": f"Auto-assignment completed. {result['assigned_students']} students assigned to classes",
        **result
    }

@router.post("/bulk/delete", response_model=dict)
async def bulk_delete_enrollments(
    delete_data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk soft delete enrollments"""
    service = EnrollmentService(db)
    
    result = await service.bulk_soft_delete_enrollments(
        enrollment_ids=delete_data.enrollment_ids
    )
    
    return {
        "message": f"Bulk delete completed. {result['deleted_enrollments']} enrollments removed",
        **result
    }

@router.get("/statistics/comprehensive")
async def get_comprehensive_enrollment_statistics(
    tenant_id: UUID,
    academic_year: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive enrollment statistics"""
    service = EnrollmentService(db)
    
    stats = await service.get_comprehensive_enrollment_statistics(
        tenant_id=tenant_id,
        academic_year=academic_year
    )
    
    return {
        "message": "Enrollment statistics retrieved successfully",
        **stats
    }

# EXISTING UTILITY ENDPOINTS (unchanged)
@router.get("/{enrollment_id}", response_model=dict)
async def get_enrollment(
    enrollment_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific enrollment details"""
    service = EnrollmentService(db)
    enrollment = await service.get(enrollment_id)
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return {
        "id": str(enrollment.id),
        "student_id": str(enrollment.student_id),
        "class_id": str(enrollment.class_id),
        "academic_year": enrollment.academic_year,
        "enrollment_date": enrollment.enrollment_date.isoformat(),
        "status": enrollment.status,
        "created_at": enrollment.created_at.isoformat(),
        "updated_at": enrollment.updated_at.isoformat()
    }

@router.put("/{enrollment_id}", response_model=dict)
async def update_enrollment(
    enrollment_id: UUID,
    enrollment_data: EnrollmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update enrollment information"""
    service = EnrollmentService(db)
    
    update_dict = enrollment_data.model_dump(exclude_unset=True)
    enrollment = await service.update(enrollment_id, update_dict)
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return {
        "id": str(enrollment.id),
        "message": "Enrollment updated successfully"
    }

@router.patch("/{enrollment_id}/status")
async def update_enrollment_status(
    enrollment_id: UUID,
    status_data: StatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update enrollment status"""
    service = EnrollmentService(db)
    
    enrollment = await service.update_enrollment_status(enrollment_id, status_data.status)
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return {
        "id": str(enrollment.id),
        "message": f"Enrollment status updated to {status_data.status}",
        "status": enrollment.status
    }

@router.delete("/{enrollment_id}")
async def delete_enrollment(
    enrollment_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete enrollment"""
    service = EnrollmentService(db)
    success = await service.soft_delete(enrollment_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return {"message": "Enrollment removed successfully"}

@router.get("/student/{student_id}")
async def get_student_enrollments(
    student_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all enrollments for a specific student"""
    service = EnrollmentService(db)
    enrollments = await service.get_by_student(student_id)
    
    return [
        {
            "id": str(enrollment.id),
            "class_id": str(enrollment.class_id),
            "academic_year": enrollment.academic_year,
            "enrollment_date": enrollment.enrollment_date.isoformat(),
            "status": enrollment.status
        }
        for enrollment in enrollments
    ]

@router.get("/class/{class_id}")
async def get_class_enrollments(
    class_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all enrollments for a specific class"""
    service = EnrollmentService(db)
    enrollments = await service.get_by_class(class_id)
    
    return [
        {
            "id": str(enrollment.id),
            "student_id": str(enrollment.student_id),
            "academic_year": enrollment.academic_year,
            "enrollment_date": enrollment.enrollment_date.isoformat(),
            "status": enrollment.status
        }
        for enrollment in enrollments
    ]

@router.get("/academic-year/{academic_year}")
async def get_enrollments_by_academic_year(
    academic_year: str,
    student_id: Optional[UUID] = Query(None),
    class_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get enrollments by academic year"""
    service = EnrollmentService(db)
    enrollments = await service.get_by_academic_year(academic_year, student_id, class_id)
    
    return [
        {
            "id": str(enrollment.id),
            "student_id": str(enrollment.student_id),
            "class_id": str(enrollment.class_id),
            "enrollment_date": enrollment.enrollment_date.isoformat(),
            "status": enrollment.status
        }
        for enrollment in enrollments
    ]
