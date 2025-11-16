# app/routers/school_authority/attendance.py
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime, timedelta
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

class AttendanceUpdateItem(BaseModel):
    user_id: UUID
    status: str
    remarks: Optional[str] = ""

class BulkAttendanceUpdate(BaseModel):
    attendance_updates: List[AttendanceUpdateItem]
    attendance_date: date
    marked_by: UUID
    marked_by_type: UserType

class BulkStaffAttendanceUpdate(BaseModel):
    attendance_updates: List[dict]  # [{"user_id": UUID, "user_type": str, "status": str, "remarks": str}]
    attendance_date: date
    marked_by: UUID
    marked_by_type: UserType

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

# CLASS-BASED ATTENDANCE

@router.get("/class/{class_id}/students-with-attendance/{attendance_date}")
async def get_class_students_with_attendance(
    class_id: UUID,
    attendance_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Get all students in class with their attendance status for a specific date"""
    try:
        students_with_attendance_sql = text("""
            SELECT 
                c.id as class_id,
                c.class_name,
                c.grade_level,
                c.section,
                c.academic_year,
                s.id as student_id,
                s.student_id as student_number,
                s.first_name,
                s.last_name,
                s.roll_number,
                a.id as attendance_id,
                a.status as attendance_status,
                a.attendance_time,
                a.remarks,
                a.is_excused
            FROM classes c
            JOIN enrollments e ON c.id = e.class_id
            JOIN students s ON e.student_id = s.id
            LEFT JOIN attendances a ON (
                s.id = a.user_id 
                AND a.attendance_date = :attendance_date 
                AND a.class_id = :class_id
                AND a.is_deleted = false
            )
            WHERE c.id = :class_id
            AND c.is_deleted = false
            AND e.status = 'active'
            AND e.is_deleted = false
            AND s.is_deleted = false
            AND s.status = 'active'
            ORDER BY s.first_name, s.last_name
        """)
        
        result = await db.execute(students_with_attendance_sql, {
            "class_id": class_id,
            "attendance_date": attendance_date
        })
        
        rows = result.fetchall()
        
        if not rows:
            raise HTTPException(status_code=404, detail="Class not found or no students enrolled")
        
        first_row = rows[0]
        class_info = {
            "id": str(first_row[0]),
            "class_name": first_row[1],
            "grade_level": first_row[2],
            "section": first_row[3],
            "academic_year": first_row[4]
        }
        
        students = []
        for row in rows:
            students.append({
                "student_id": str(row[5]),
                "student_number": row[6],
                "first_name": row[7],
                "last_name": row[8],
                "full_name": f"{row[7]} {row[8]}",
                "roll_number": row[9],
                "attendance_id": str(row[10]) if row[10] else None,
                "attendance_status": row[11] if row[11] else "not_marked",
                "attendance_time": row[12].isoformat() if row[12] else None,
                "remarks": row[13],
                "is_excused": row[14] if row[14] is not None else False
            })
        
        return {
            "class_info": class_info,
            "attendance_date": attendance_date.isoformat(),
            "students": students,
            "total_students": len(students),
            "marked_count": len([s for s in students if s["attendance_status"] != "not_marked"]),
            "present_count": len([s for s in students if s["attendance_status"] == "present"]),
            "absent_count": len([s for s in students if s["attendance_status"] == "absent"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get class attendance: {str(e)}")

@router.post("/class/{class_id}/bulk-update-attendance")
async def bulk_update_class_attendance(
    class_id: UUID,
    request: BulkAttendanceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update attendance for multiple students in a class"""
    service = AttendanceService(db)
    
    try:
        attendance_records = []
        for update in request.attendance_updates:
            attendance_records.append({
                "user_id": update.user_id,
                "user_type": "STUDENT",
                "class_id": class_id,
                "attendance_date": request.attendance_date,
                "status": update.status.upper(),
                "remarks": update.remarks or "",
                "marked_by": request.marked_by,
                "marked_by_type": request.marked_by_type.value.upper(),
                "attendance_type": "DAILY",
                "academic_year": "2025-26"
            })
        
        class_sql = text("SELECT tenant_id FROM classes WHERE id = :class_id")
        class_result = await db.execute(class_sql, {"class_id": class_id})
        tenant_row = class_result.fetchone()
        
        if not tenant_row:
            raise HTTPException(status_code=404, detail="Class not found")
        
        tenant_id = tenant_row[0]
        
        result = await service.bulk_mark_attendance(
            attendance_records=attendance_records,
            tenant_id=tenant_id
        )
        
        return {
            "message": f"Successfully updated attendance for {result['successful_records']} students",
            "class_id": str(class_id),
            "attendance_date": request.attendance_date.isoformat(),
            "updated_students": result["successful_records"],
            "failed_updates": result["failed_records"],
            "total_processed": len(request.attendance_updates)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update class attendance: {str(e)}")

# GRADE-LEVEL ATTENDANCE

@router.get("/grade/{tenant_id}/{grade_level}/{section}/students-with-attendance/{attendance_date}")
async def get_grade_students_with_attendance(
    tenant_id: UUID,
    grade_level: int,
    section: str,
    attendance_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Get all students in a grade+section with their attendance status for a specific date"""
    try:
        students_with_attendance_sql = text("""
            SELECT 
                s.id as student_id,
                s.student_id as student_number,
                s.first_name,
                s.last_name,
                s.roll_number,
                s.grade_level,
                s.section,
                a.id as attendance_id,
                a.status as attendance_status,
                a.attendance_time,
                a.remarks,
                a.is_excused
            FROM students s
            LEFT JOIN (
                SELECT DISTINCT ON (user_id) 
                    id, user_id, status, attendance_time, remarks, is_excused
                FROM attendances 
                WHERE attendance_date = :attendance_date 
                AND user_type = 'STUDENT'
                AND class_id IS NULL
                AND is_deleted = false
                ORDER BY user_id, attendance_time DESC
            ) a ON s.id = a.user_id
            WHERE s.tenant_id = :tenant_id
            AND s.grade_level = :grade_level
            AND s.section = :section
            AND s.is_deleted = false
            AND s.status = 'active'
            ORDER BY s.first_name, s.last_name
        """)
        
        result = await db.execute(students_with_attendance_sql, {
            "tenant_id": tenant_id,
            "grade_level": grade_level,
            "section": section,
            "attendance_date": attendance_date
        })
        
        rows = result.fetchall()
        
        students = []
        for row in rows:
            students.append({
                "student_id": str(row[0]),
                "student_number": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "full_name": f"{row[2]} {row[3]}",
                "roll_number": row[4],
                "grade_level": row[5],
                "section": row[6],
                "attendance_id": str(row[7]) if row[7] else None,
                "attendance_status": row[8] if row[8] else "not_marked",
                "attendance_time": row[9].isoformat() if row[9] else None,
                "remarks": row[10],
                "is_excused": row[11] if row[11] is not None else False
            })
        
        return {
            "grade_info": {
                "grade_level": grade_level,
                "section": section,
                "tenant_id": str(tenant_id)
            },
            "attendance_date": attendance_date.isoformat(),
            "students": students,
            "total_students": len(students),
            "marked_count": len([s for s in students if s["attendance_status"] != "not_marked"]),
            "present_count": len([s for s in students if s["attendance_status"] == "PRESENT"]),
            "absent_count": len([s for s in students if s["attendance_status"] == "ABSENT"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get grade attendance: {str(e)}")

@router.post("/grade/{tenant_id}/{grade_level}/{section}/bulk-update-attendance")
async def bulk_update_grade_attendance(
    tenant_id: UUID,
    grade_level: int,
    section: str,
    request: BulkAttendanceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update attendance for students in a grade+section"""
    service = AttendanceService(db)
    
    try:
        attendance_records = []
        for update in request.attendance_updates:
            attendance_records.append({
                "user_id": update.user_id,
                "user_type": "STUDENT",
                "class_id": None,  # Grade-level attendance has no class_id
                "attendance_date": request.attendance_date,
                "status": update.status.upper(),
                "remarks": update.remarks or "",
                "marked_by": request.marked_by,
                "marked_by_type": request.marked_by_type.value.upper(),
                "attendance_type": "DAILY",
                "academic_year": "2025-26"
            })
        
        result = await service.bulk_mark_attendance(
            attendance_records=attendance_records,
            tenant_id=tenant_id
        )
        
        return {
            "message": f"Successfully updated attendance for {result['successful_records']} students",
            "grade_level": grade_level,
            "section": section,
            "attendance_date": request.attendance_date.isoformat(),
            "updated_students": result["successful_records"],
            "failed_updates": result["failed_records"],
            "total_processed": len(request.attendance_updates)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update grade attendance: {str(e)}")

# STAFF ATTENDANCE

@router.get("/staff/{tenant_id}/with-attendance/{attendance_date}")
async def get_staff_with_attendance(
    tenant_id: UUID,
    attendance_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Get all teachers and school authorities with their attendance status"""
    try:
        teachers_sql = text("""
            SELECT 
                t.id as user_id,
                t.teacher_id as user_number,
                t.first_name,
                t.last_name,
                'TEACHER' as user_type,
                t.position,
                a.id as attendance_id,
                a.status as attendance_status,
                a.attendance_time,
                a.remarks,
                a.is_excused
            FROM teachers t
            LEFT JOIN (
                SELECT DISTINCT ON (user_id) 
                    id, user_id, status, attendance_time, remarks, is_excused
                FROM attendances 
                WHERE attendance_date = :attendance_date 
                AND user_type = 'TEACHER'
                AND is_deleted = false
                ORDER BY user_id, attendance_time DESC
            ) a ON t.id = a.user_id
            WHERE t.tenant_id = :tenant_id
            AND t.is_deleted = false
            AND t.status = 'active'
        """)
        
        authorities_sql = text("""
            SELECT 
                sa.id as user_id,
                sa.authority_id as user_number,
                sa.first_name,
                sa.last_name,
                'SCHOOL_AUTHORITY' as user_type,
                sa.role as position,
                a.id as attendance_id,
                a.status as attendance_status,
                a.attendance_time,
                a.remarks,
                a.is_excused
            FROM school_authorities sa
            LEFT JOIN (
                SELECT DISTINCT ON (user_id) 
                    id, user_id, status, attendance_time, remarks, is_excused
                FROM attendances 
                WHERE attendance_date = :attendance_date 
                AND user_type = 'SCHOOL_AUTHORITY'
                AND is_deleted = false
                ORDER BY user_id, attendance_time DESC
            ) a ON sa.id = a.user_id
            WHERE sa.tenant_id = :tenant_id
            AND sa.is_deleted = false
            AND sa.status = 'active'
        """)
        
        params = {"tenant_id": tenant_id, "attendance_date": attendance_date}
        
        teachers_result = await db.execute(teachers_sql, params)
        authorities_result = await db.execute(authorities_sql, params)
        
        all_staff = []
        
        for row in teachers_result.fetchall():
            all_staff.append({
                "user_id": str(row[0]),
                "user_number": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "full_name": f"{row[2]} {row[3]}",
                "user_type": row[4],
                "position": row[5],
                "attendance_id": str(row[6]) if row[6] else None,
                "attendance_status": row[7] if row[7] else "not_marked",
                "attendance_time": row[8].isoformat() if row[8] else None,
                "remarks": row[9],
                "is_excused": row[10] if row[10] is not None else False
            })
        
        for row in authorities_result.fetchall():
            all_staff.append({
                "user_id": str(row[0]),
                "user_number": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "full_name": f"{row[2]} {row[3]}",
                "user_type": row[4],
                "position": row[5],
                "attendance_id": str(row[6]) if row[6] else None,
                "attendance_status": row[7] if row[7] else "not_marked",
                "attendance_time": row[8].isoformat() if row[8] else None,
                "remarks": row[9],
                "is_excused": row[10] if row[10] is not None else False
            })
        

        
        return {
            "attendance_date": attendance_date.isoformat(),
            "staff": all_staff,
            "total_staff": len(all_staff),
            "marked_count": len([s for s in all_staff if s["attendance_status"] != "not_marked"]),
            "present_count": len([s for s in all_staff if s["attendance_status"] == "PRESENT"]),
            "absent_count": len([s for s in all_staff if s["attendance_status"] == "ABSENT"]),
            "late_count": len([s for s in all_staff if s["attendance_status"] == "LATE"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get staff attendance: {str(e)}")

@router.post("/staff/{tenant_id}/bulk-update-attendance")
async def bulk_update_staff_attendance(
    tenant_id: UUID,
    request: BulkStaffAttendanceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update attendance for teachers, school authorities, and staff"""
    service = AttendanceService(db)
    
    try:
        attendance_records = []
        for update in request.attendance_updates:
            attendance_records.append({
                "user_id": update["user_id"],
                "user_type": update["user_type"].upper(),
                "attendance_date": request.attendance_date,
                "status": update["status"].upper(),
                "remarks": update.get("remarks", ""),
                "marked_by": request.marked_by,
                "marked_by_type": request.marked_by_type.value.upper(),
                "attendance_type": "DAILY",
                "academic_year": "2025-26"
            })
        
        result = await service.bulk_mark_attendance(
            attendance_records=attendance_records,
            tenant_id=tenant_id
        )
        
        return {
            "message": f"Successfully updated attendance for {result['successful_records']} staff members",
            "attendance_date": request.attendance_date.isoformat(),
            "updated_staff": result["successful_records"],
            "failed_updates": result["failed_records"],
            "total_processed": len(request.attendance_updates)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update staff attendance: {str(e)}")

# STUDENT ATTENDANCE HISTORY

@router.get("/students/{tenant_id}/filter")
async def get_students_for_filter(
    tenant_id: UUID,
    grade_level: int = None,
    section: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get students filtered by grade and section for attendance history selection"""
    try:
        sql = text("""
            SELECT 
                s.id,
                s.student_id,
                s.first_name,
                s.last_name,
                s.grade_level,
                s.section
            FROM students s
            WHERE s.tenant_id = :tenant_id
            AND s.is_deleted = false
            AND s.status = 'active'
            AND (:grade_level::INTEGER IS NULL OR s.grade_level = :grade_level::INTEGER)
            AND (:section::VARCHAR IS NULL OR s.section = :section::VARCHAR)
            ORDER BY s.grade_level, s.section, s.first_name, s.last_name
        """)
        
        result = await db.execute(sql, {
            "tenant_id": tenant_id, 
            "grade_level": grade_level,
            "section": section
        })
        
        students = []
        for row in result.fetchall():
            students.append({
                "id": str(row[0]),
                "student_id": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "full_name": f"{row[2]} {row[3]}",
                "grade_level": row[4],
                "section": row[5]
            })
        
        return {"students": students}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get students: {str(e)}")

# STAFF ATTENDANCE HISTORY

@router.get("/staff/{tenant_id}/filter")
async def get_staff_for_filter(
    tenant_id: UUID,
    user_type: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get staff (teachers and school authorities) for attendance history selection"""
    try:
        staff = []
        
        # Get teachers if no filter or specifically TEACHER
        if not user_type or user_type == 'TEACHER':
            teachers_sql = text("""
                SELECT 
                    t.id,
                    t.teacher_id,
                    t.first_name,
                    t.last_name,
                    'TEACHER' as user_type,
                    t.position
                FROM teachers t
                WHERE t.tenant_id = :tenant_id
                AND t.is_deleted = false
                AND t.status = 'active'
                ORDER BY t.first_name, t.last_name
            """)
            
            teachers_result = await db.execute(teachers_sql, {"tenant_id": tenant_id})
            for row in teachers_result.fetchall():
                staff.append({
                    "id": str(row[0]),
                    "staff_id": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                    "full_name": f"{row[2]} {row[3]}",
                    "user_type": row[4],
                    "position": row[5]
                })
        
        # Get school authorities if no filter or specifically SCHOOL_AUTHORITY
        if not user_type or user_type == 'SCHOOL_AUTHORITY':
            authorities_sql = text("""
                SELECT 
                    sa.id,
                    sa.authority_id,
                    sa.first_name,
                    sa.last_name,
                    'SCHOOL_AUTHORITY' as user_type,
                    sa.role as position
                FROM school_authorities sa
                WHERE sa.tenant_id = :tenant_id
                AND sa.is_deleted = false
                AND sa.status = 'active'
                ORDER BY sa.first_name, sa.last_name
            """)
            
            authorities_result = await db.execute(authorities_sql, {"tenant_id": tenant_id})
            for row in authorities_result.fetchall():
                staff.append({
                    "id": str(row[0]),
                    "staff_id": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                    "full_name": f"{row[2]} {row[3]}",
                    "user_type": row[4],
                    "position": row[5]
                })
        
        return {"staff": staff}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get staff: {str(e)}")

@router.get("/staff/{tenant_id}/{staff_id}/history")
async def get_staff_attendance_history(
    tenant_id: UUID,
    staff_id: UUID,
    start_date: date = None,
    end_date: date = None,
    db: AsyncSession = Depends(get_db)
):
    """Get attendance history for a specific staff member (teacher or school authority)"""
    try:
        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        sql = text("""
            SELECT 
                a.attendance_date,
                a.status,
                a.attendance_time,
                a.remarks,
                a.is_excused,
                a.user_type
            FROM attendances a
            WHERE a.user_id = :staff_id
            AND a.user_type IN ('TEACHER', 'SCHOOL_AUTHORITY')
            AND a.attendance_date BETWEEN :start_date AND :end_date
            AND a.is_deleted = false
            ORDER BY a.attendance_date DESC
        """)
        
        result = await db.execute(sql, {
            "staff_id": staff_id,
            "start_date": start_date,
            "end_date": end_date
        })
        
        # Group by date
        history_by_date = {}
        for row in result.fetchall():
            date_str = row[0].isoformat()
            if date_str not in history_by_date:
                history_by_date[date_str] = {
                    "date": date_str,
                    "attendance": None
                }
            
            history_by_date[date_str]["attendance"] = {
                "status": row[1],
                "attendance_time": row[2].isoformat() if row[2] else None,
                "remarks": row[3],
                "is_excused": row[4],
                "user_type": row[5]
            }
        
        return {
            "staff_id": str(staff_id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "attendance_history": list(history_by_date.values())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get staff attendance history: {str(e)}")

@router.get("/student/{tenant_id}/{student_id}/history")
async def get_student_attendance_history_singular(
    tenant_id: UUID,
    student_id: UUID,
    start_date: date = None,
    end_date: date = None,
    db: AsyncSession = Depends(get_db)
):
    """Get attendance history for a specific student (both grade and class level) - singular endpoint"""
    try:
        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        sql = text("""
            SELECT 
                a.attendance_date,
                a.status,
                a.attendance_type,
                a.period_number,
                a.subject_name,
                a.class_id,
                a.remarks,
                a.is_excused,
                c.class_name
            FROM attendances a
            LEFT JOIN classes c ON a.class_id = c.id
            WHERE a.user_id = :student_id
            AND a.user_type = 'STUDENT'
            AND a.attendance_date BETWEEN :start_date AND :end_date
            AND a.is_deleted = false
            ORDER BY a.attendance_date DESC, a.period_number ASC
        """)
        
        result = await db.execute(sql, {
            "student_id": student_id,
            "start_date": start_date,
            "end_date": end_date
        })
        
        # Group by date
        history_by_date = {}
        for row in result.fetchall():
            date_str = row[0].isoformat()
            if date_str not in history_by_date:
                history_by_date[date_str] = {
                    "date": date_str,
                    "grade_attendance": None,
                    "class_attendance": []
                }
            
            attendance_record = {
                "status": row[1],
                "period_number": row[3],
                "subject_name": row[4],
                "class_id": str(row[5]) if row[5] else None,
                "class_name": row[8],
                "remarks": row[6],
                "is_excused": row[7]
            }
            
            # Grade level attendance: class_id is NULL
            if row[5] is None:  # No class_id means grade-level attendance
                history_by_date[date_str]["grade_attendance"] = attendance_record
            else:  # Has class_id means class-level attendance
                history_by_date[date_str]["class_attendance"].append(attendance_record)
        
        return {
            "student_id": str(student_id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "attendance_history": list(history_by_date.values())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attendance history: {str(e)}")

@router.get("/students/{tenant_id}/{student_id}/history")
async def get_student_attendance_history(
    tenant_id: UUID,
    student_id: UUID,
    start_date: date = None,
    end_date: date = None,
    db: AsyncSession = Depends(get_db)
):
    """Get attendance history for a specific student (both grade and class level)"""
    try:
        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        sql = text("""
            SELECT 
                a.attendance_date,
                a.status,
                a.attendance_type,
                a.period_number,
                a.subject_name,
                a.class_id,
                a.remarks,
                a.is_excused,
                c.class_name
            FROM attendances a
            LEFT JOIN classes c ON a.class_id = c.id
            WHERE a.user_id = :student_id
            AND a.user_type = 'STUDENT'
            AND a.attendance_date BETWEEN :start_date AND :end_date
            AND a.is_deleted = false
            ORDER BY a.attendance_date DESC, a.period_number ASC
        """)
        
        result = await db.execute(sql, {
            "student_id": student_id,
            "start_date": start_date,
            "end_date": end_date
        })
        
        # Group by date
        history_by_date = {}
        for row in result.fetchall():
            date_str = row[0].isoformat()
            if date_str not in history_by_date:
                history_by_date[date_str] = {
                    "date": date_str,
                    "grade_attendance": None,
                    "class_attendance": []
                }
            
            attendance_record = {
                "status": row[1],
                "period_number": row[3],
                "subject_name": row[4],
                "class_id": str(row[5]) if row[5] else None,
                "class_name": row[8],
                "remarks": row[6],
                "is_excused": row[7]
            }
            
            # Grade level attendance: class_id is NULL
            if row[5] is None:  # No class_id means grade-level attendance
                history_by_date[date_str]["grade_attendance"] = attendance_record
            else:  # Has class_id means class-level attendance
                history_by_date[date_str]["class_attendance"].append(attendance_record)
        
        return {
            "student_id": str(student_id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "attendance_history": list(history_by_date.values())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attendance history: {str(e)}")

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
