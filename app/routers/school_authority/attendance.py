from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.attendance_service import AttendanceService
from ...models.tenant_specific.attendance import AttendanceStatus, AttendanceType

router = APIRouter(prefix="/api/v1/school_authority/attendance", tags=["School Authority - Attendance Management"])

@router.post("/mark", response_model=dict)
async async def mark_attendance(
    attendance_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance for a student"""
    service = AttendanceService(db)
    
    try:
        attendance = service.mark_attendance(attendance_data)
        return {
            "id": str(attendance.id),
            "message": "Attendance marked successfully",
            "student_id": str(attendance.student_id),
            "date": attendance.date.isoformat(),
            "status": attendance.status.value
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bulk-mark", response_model=dict)
async async def bulk_mark_attendance(
    attendance_records: List[dict],
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance for multiple students"""
    service = AttendanceService(db)
    
    try:
        created_records = service.bulk_mark_attendance(attendance_records)
        return {
            "message": f"Attendance marked for {len(created_records)} students",
            "total_processed": len(attendance_records),
            "successful": len(created_records),
            "failed": len(attendance_records) - len(created_records)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/student/{student_id}", response_model=List[dict])
async async def get_student_attendance(
    student_id: UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    attendance_type: Optional[AttendanceType] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance records for a specific student"""
    service = AttendanceService(db)
    
    try:
        attendances = service.get_student_attendance(
            student_id=student_id,
            start_date=start_date,
            end_date=end_date,
            attendance_type=attendance_type
        )
        
        return [
            {
                "id": str(att.id),
                "date": att.date.isoformat(),
                "status": att.status.value,
                "attendance_type": att.attendance_type.value,
                "check_in_time": att.check_in_time.isoformat() if att.check_in_time else None,
                "check_out_time": att.check_out_time.isoformat() if att.check_out_time else None,
                "period_number": att.period_number,
                "subject": att.subject,
                "remarks": att.remarks,
                "reason_for_absence": att.reason_for_absence,
                "is_excused": att.is_excused,
                "class_id": str(att.class_id) if att.class_id else None,
                "teacher_id": str(att.teacher_id) if att.teacher_id else None
            }
            for att in attendances
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/class/{class_id}", response_model=List[dict])
async async def get_class_attendance(
    class_id: UUID,
    attendance_date: date,
    period_number: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance for all students in a class for a specific date"""
    service = AttendanceService(db)
    
    try:
        attendances = service.get_class_attendance(
            class_id=class_id,
            attendance_date=attendance_date,
            period_number=period_number
        )
        
        return [
            {
                "id": str(att.id),
                "student_id": str(att.student_id),
                "date": att.date.isoformat(),
                "status": att.status.value,
                "attendance_type": att.attendance_type.value,
                "check_in_time": att.check_in_time.isoformat() if att.check_in_time else None,
                "period_number": att.period_number,
                "subject": att.subject,
                "remarks": att.remarks,
                "teacher_id": str(att.teacher_id) if att.teacher_id else None
            }
            for att in attendances
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/statistics", response_model=dict)
async async def get_attendance_statistics(
    student_id: Optional[UUID] = Query(None),
    class_id: Optional[UUID] = Query(None),
    tenant_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance statistics"""
    service = AttendanceService(db)
    
    try:
        stats = service.get_attendance_statistics(
            student_id=student_id,
            class_id=class_id,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/low-attendance/{tenant_id}", response_model=List[dict])
async async def get_low_attendance_students(
    tenant_id: UUID,
    threshold_percentage: int = Query(75, ge=0, le=100),
    academic_year: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get students with attendance below threshold"""
    service = AttendanceService(db)
    
    try:
        students = service.get_low_attendance_students(
            tenant_id=tenant_id,
            threshold_percentage=threshold_percentage,
            academic_year=academic_year
        )
        return students
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/absent-today/{tenant_id}", response_model=List[dict])
async async def get_absent_students_today(
    tenant_id: UUID,
    class_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get students who are absent today"""
    service = AttendanceService(db)
    
    try:
        absent_students = service.get_absent_students_today(
            tenant_id=tenant_id,
            class_id=class_id
        )
        
        return [
            {
                "id": str(att.id),
                "student_id": str(att.student_id),
                "class_id": str(att.class_id) if att.class_id else None,
                "date": att.date.isoformat(),
                "reason_for_absence": att.reason_for_absence,
                "is_excused": att.is_excused
            }
            for att in absent_students
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/monthly-summary/{student_id}", response_model=dict)
async async def get_monthly_attendance_summary(
    student_id: UUID,
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db)
):
    """Get monthly attendance summary for a student"""
    service = AttendanceService(db)
    
    try:
        summary = service.get_monthly_attendance_summary(
            student_id=student_id,
            year=year,
            month=month
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{attendance_id}/approve", response_model=dict)
async async def approve_absence(
    attendance_id: UUID,
    approval_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Approve an absence"""
    service = AttendanceService(db)
    
    try:
        attendance = service.approve_absence(
            attendance_id=attendance_id,
            approved_by=approval_data.get("approved_by"),
            approval_remarks=approval_data.get("approval_remarks")
        )
        
        if not attendance:
            raise HTTPException(status_code=404, detail="Attendance record not found")
        
        return {
            "id": str(attendance.id),
            "message": "Absence approved successfully",
            "is_excused": attendance.is_excused,
            "approved_by": str(attendance.approved_by) if attendance.approved_by else None,
            "approval_date": attendance.approval_date.isoformat() if attendance.approval_date else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{attendance_id}", response_model=dict)
async async def get_attendance_record(
    attendance_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific attendance record"""
    service = AttendanceService(db)
    attendance = service.get(attendance_id)
    
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    return {
        "id": str(attendance.id),
        "tenant_id": str(attendance.tenant_id),
        "student_id": str(attendance.student_id),
        "class_id": str(attendance.class_id) if attendance.class_id else None,
        "teacher_id": str(attendance.teacher_id) if attendance.teacher_id else None,
        "date": attendance.date.isoformat(),
        "attendance_type": attendance.attendance_type.value,
        "status": attendance.status.value,
        "check_in_time": attendance.check_in_time.isoformat() if attendance.check_in_time else None,
        "check_out_time": attendance.check_out_time.isoformat() if attendance.check_out_time else None,
        "expected_check_in": attendance.expected_check_in.isoformat() if attendance.expected_check_in else None,
        "expected_check_out": attendance.expected_check_out.isoformat() if attendance.expected_check_out else None,
        "period_number": attendance.period_number,
        "subject": attendance.subject,
        "remarks": attendance.remarks,
        "reason_for_absence": attendance.reason_for_absence,
        "is_excused": attendance.is_excused,
        "approved_by": str(attendance.approved_by) if attendance.approved_by else None,
        "approval_date": attendance.approval_date.isoformat() if attendance.approval_date else None,
        "approval_remarks": attendance.approval_remarks,
        "academic_year": attendance.academic_year,
        "term": attendance.term,
        "created_at": attendance.created_at.isoformat(),
        "updated_at": attendance.updated_at.isoformat()
    }
