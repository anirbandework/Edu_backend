# app/routers/school_authority/attendance.py
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from ...core.database import get_db
from ...services.attendance_service import AttendanceService
from ...models.tenant_specific.attendance import AttendanceStatus, AttendanceType, UserType

# Pydantic Models
class AttendanceCreate(BaseModel):
    user_id: UUID
    user_type: UserType
    class_id: Optional[UUID] = None
    attendance_date: Optional[date] = None
    attendance_type: AttendanceType = AttendanceType.DAILY
    status: AttendanceStatus = AttendanceStatus.PRESENT
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    period_number: Optional[int] = None
    subject_name: Optional[str] = None
    location: Optional[str] = None
    remarks: Optional[str] = None
    reason_for_absence: Optional[str] = None
    academic_year: Optional[str] = None
    term: Optional[str] = None

class BulkAttendanceCreate(BaseModel):
    tenant_id: UUID
    attendance_records: List[dict]

class BulkStatusUpdate(BaseModel):
    attendance_ids: List[UUID]
    new_status: str
    updated_by: UUID

class BulkApproveAbsences(BaseModel):
    attendance_ids: List[UUID]
    approved_by: UUID
    approval_remarks: Optional[str] = None

router = APIRouter(prefix="/api/v1/school_authority/attendance", tags=["School Authority - Attendance Management"])

# MAIN ATTENDANCE MARKING ENDPOINTS

@router.post("/mark", response_model=dict)
async def mark_attendance(
    attendance_data: AttendanceCreate,
    marked_by: UUID,
    marked_by_type: UserType,
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance for a user (student, teacher, or staff)"""
    service = AttendanceService(db)
    
    try:
        attendance = await service.mark_attendance(
            user_id=attendance_data.user_id,
            user_type=attendance_data.user_type,
            marked_by=marked_by,
            marked_by_type=marked_by_type,
            attendance_data=attendance_data.model_dump(exclude={"user_id", "user_type"})
        )
        
        return {
            "id": str(attendance.id),
            "message": "Attendance marked successfully",
            "user_id": str(attendance.user_id),
            "user_type": attendance.user_type.value,
            "attendance_date": attendance.attendance_date.isoformat(),
            "status": attendance.status.value
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/mark/student", response_model=dict)
async def mark_student_attendance(
    attendance_data: AttendanceCreate,
    marked_by: UUID,
    marked_by_type: UserType,
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance for a student (can be marked by teacher or school authority)"""
    attendance_data.user_type = UserType.STUDENT
    
    return await mark_attendance(attendance_data, marked_by, marked_by_type, db)

@router.post("/mark/teacher", response_model=dict)
async def mark_teacher_attendance(
    attendance_data: AttendanceCreate,
    marked_by: UUID,
    marked_by_type: UserType,
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance for a teacher (can be self-marked or by school authority)"""
    attendance_data.user_type = UserType.TEACHER
    
    return await mark_attendance(attendance_data, marked_by, marked_by_type, db)

@router.post("/mark/authority", response_model=dict)
async def mark_authority_attendance(
    attendance_data: AttendanceCreate,
    marked_by: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance for school authority (self-marked)"""
    attendance_data.user_type = UserType.SCHOOL_AUTHORITY
    
    return await mark_attendance(attendance_data, marked_by, UserType.SCHOOL_AUTHORITY, db)

# BULK OPERATIONS

@router.post("/bulk/mark", response_model=dict)
async def bulk_mark_attendance(
    import_data: BulkAttendanceCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Bulk mark attendance for multiple users"""
    service = AttendanceService(db)
    
    result = await service.bulk_mark_attendance(
        attendance_records=import_data.attendance_records,
        tenant_id=import_data.tenant_id
    )
    
    return {
        "message": f"Bulk attendance marking completed. {result['successful_records']} records processed successfully",
        **result
    }

@router.post("/bulk/update-status", response_model=dict)
async def bulk_update_status(
    status_data: BulkStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update attendance status"""
    service = AttendanceService(db)
    
    result = await service.bulk_update_attendance_status(
        attendance_ids=status_data.attendance_ids,
        new_status=status_data.new_status,
        updated_by=status_data.updated_by
    )
    
    return {
        "message": f"Status update completed. {result['updated_records']} records updated to '{result['new_status']}'",
        **result
    }

@router.post("/bulk/approve-absences", response_model=dict)
async def bulk_approve_absences(
    approval_data: BulkApproveAbsences,
    db: AsyncSession = Depends(get_db)
):
    """Bulk approve absences"""
    service = AttendanceService(db)
    
    result = await service.bulk_approve_absences(
        attendance_ids=approval_data.attendance_ids,
        approved_by=approval_data.approved_by,
        approval_remarks=approval_data.approval_remarks
    )
    
    return {
        "message": f"Bulk approval completed. {result['approved_records']} absences approved",
        **result
    }

# ATTENDANCE RETRIEVAL

@router.get("/user/{user_id}")
async def get_user_attendance(
    user_id: UUID,
    user_type: UserType,
    requester_id: UUID,
    requester_type: UserType,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    attendance_type: Optional[AttendanceType] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance records for a specific user"""
    service = AttendanceService(db)
    
    try:
        attendances = await service.get_user_attendance(
            user_id=user_id,
            user_type=user_type,
            requester_id=requester_id,
            requester_type=requester_type,
            start_date=start_date,
            end_date=end_date,
            attendance_type=attendance_type
        )
        
        return [
            {
                "id": str(att.id),
                "user_id": str(att.user_id),
                "user_type": att.user_type.value,
                "attendance_date": att.attendance_date.isoformat(),
                "attendance_time": att.attendance_time.isoformat(),
                "status": att.status.value,
                "attendance_type": att.attendance_type.value,
                "check_in_time": att.check_in_time.isoformat() if att.check_in_time else None,
                "check_out_time": att.check_out_time.isoformat() if att.check_out_time else None,
                "period_number": att.period_number,
                "subject_name": att.subject_name,
                "location": att.location,
                "remarks": att.remarks,
                "reason_for_absence": att.reason_for_absence,
                "is_excused": att.is_excused,
                "marked_by": str(att.marked_by),
                "marked_by_type": att.marked_by_type.value,
                "class_id": str(att.class_id) if att.class_id else None
            }
            for att in attendances
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ANALYTICS AND REPORTING

@router.get("/dashboard/{tenant_id}")
async def get_attendance_dashboard(
    tenant_id: UUID,
    user_type: Optional[UserType] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive attendance dashboard statistics"""
    service = AttendanceService(db)
    
    date_range = {}
    if start_date:
        date_range["start_date"] = start_date
    if end_date:
        date_range["end_date"] = end_date
    
    stats = await service.get_attendance_dashboard_stats(
        tenant_id=tenant_id,
        user_type=user_type,
        date_range=date_range if date_range else None
    )
    
    return {
        "message": "Attendance dashboard data retrieved successfully",
        **stats
    }

@router.get("/low-attendance/{tenant_id}")
async def get_low_attendance_users(
    tenant_id: UUID,
    threshold_percentage: int = Query(75, ge=0, le=100),
    user_type: Optional[UserType] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get users with attendance below threshold"""
    service = AttendanceService(db)
    
    try:
        users = await service.get_low_attendance_users(
            tenant_id=tenant_id,
            threshold_percentage=threshold_percentage,
            user_type=user_type
        )
        
        return {
            "threshold_percentage": threshold_percentage,
            "low_attendance_users": users,
            "total_flagged_users": len(users),
            "tenant_id": str(tenant_id)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# CLASS-BASED ATTENDANCE

@router.get("/class/{class_id}/date/{attendance_date}")
async def get_class_attendance(
    class_id: UUID,
    attendance_date: date,
    period_number: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance for all students in a class for a specific date"""
    service = AttendanceService(db)
    
    try:
        # Use raw SQL for better performance with class attendance
        base_where = """
            WHERE a.class_id = :class_id 
            AND a.attendance_date = :attendance_date
            AND a.user_type = 'student'
            AND a.is_deleted = false
        """
        
        params = {
            "class_id": class_id,
            "attendance_date": attendance_date
        }
        
        if period_number:
            base_where += " AND a.period_number = :period_number"
            params["period_number"] = period_number
        
        class_attendance_sql = text(f"""
            SELECT 
                a.id, a.user_id, a.attendance_date, a.attendance_time,
                a.status, a.attendance_type, a.check_in_time, a.check_out_time,
                a.period_number, a.subject_name, a.remarks, a.is_excused,
                a.marked_by, a.marked_by_type
            FROM attendances a
            {base_where}
            ORDER BY a.attendance_time DESC
        """)
        
        result = await db.execute(class_attendance_sql, params)
        attendances = result.fetchall()
        
        return [
            {
                "id": str(att[0]),
                "user_id": str(att[1]),
                "attendance_date": att[2].isoformat(),
                "attendance_time": att[3].isoformat(),
                "status": att[4],
                "attendance_type": att[5],
                "check_in_time": att[6].isoformat() if att[6] else None,
                "check_out_time": att[7].isoformat() if att[7] else None,
                "period_number": att[8],
                "subject_name": att[9],
                "remarks": att[10],
                "is_excused": att[11],
                "marked_by": str(att[12]),
                "marked_by_type": att[13]
            }
            for att in attendances
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{attendance_id}")
async def get_attendance_record(
    attendance_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific attendance record"""
    service = AttendanceService(db)
    attendance = await service.get(attendance_id)
    
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    return {
        "id": str(attendance.id),
        "tenant_id": str(attendance.tenant_id),
        "user_id": str(attendance.user_id),
        "user_type": attendance.user_type.value,
        "class_id": str(attendance.class_id) if attendance.class_id else None,
        "marked_by": str(attendance.marked_by),
        "marked_by_type": attendance.marked_by_type.value,
        "attendance_date": attendance.attendance_date.isoformat(),
        "attendance_time": attendance.attendance_time.isoformat(),
        "attendance_type": attendance.attendance_type.value,
        "attendance_mode": attendance.attendance_mode.value,
        "status": attendance.status.value,
        "check_in_time": attendance.check_in_time.isoformat() if attendance.check_in_time else None,
        "check_out_time": attendance.check_out_time.isoformat() if attendance.check_out_time else None,
        "expected_check_in": attendance.expected_check_in.isoformat() if attendance.expected_check_in else None,
        "expected_check_out": attendance.expected_check_out.isoformat() if attendance.expected_check_out else None,
        "period_number": attendance.period_number,
        "subject_name": attendance.subject_name,
        "location": attendance.location,
        "remarks": attendance.remarks,
        "reason_for_absence": attendance.reason_for_absence,
        "is_excused": attendance.is_excused,
        "approved_by": str(attendance.approved_by) if attendance.approved_by else None,
        "approval_date": attendance.approval_date.isoformat() if attendance.approval_date else None,
        "approval_remarks": attendance.approval_remarks,
        "academic_year": attendance.academic_year,
        "term": attendance.term,
        "latitude": attendance.latitude,
        "longitude": attendance.longitude,
        "created_at": attendance.created_at.isoformat(),
        "updated_at": attendance.updated_at.isoformat()
    }
