# app/services/attendance_service.py
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
import uuid
from datetime import datetime, date, timedelta, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func, and_, or_, desc
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from .base_service import BaseService
from ..models.tenant_specific.attendance import (
    Attendance, AttendanceSummary, AttendancePolicy, AttendanceReport, AttendanceAlert,
    AttendanceStatus, AttendanceType, UserType, AttendanceMode
)


class AttendanceService(BaseService[Attendance]):
    def __init__(self, db: AsyncSession):
        super().__init__(Attendance, db)
    
    async def mark_attendance(
        self, 
        user_id: UUID,
        user_type: UserType,
        marked_by: UUID,
        marked_by_type: UserType,
        attendance_data: dict
    ) -> Attendance:
        """Mark attendance with role-based validation"""
        
        # Validate permissions
        if not await self._validate_marking_permissions(marked_by, marked_by_type, user_id, user_type):
            raise HTTPException(status_code=403, detail="Insufficient permissions to mark attendance")
        
        # Check if attendance already exists
        attendance_date = attendance_data.get("attendance_date", date.today())
        period_number = attendance_data.get("period_number")
        attendance_type = attendance_data.get("attendance_type", AttendanceType.DAILY)
        
        existing = await self._get_existing_attendance(
            user_id, attendance_date, attendance_type, period_number
        )
        
        if existing:
            # Update existing attendance
            for key, value in attendance_data.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)
            
            existing.marked_by = marked_by
            existing.marked_by_type = marked_by_type
            existing.attendance_time = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(existing)
            
            # Trigger alerts if needed
            await self._check_and_create_alerts(existing)
            
            return existing
        else:
            # Create new attendance record
            attendance_record = {
                "user_id": user_id,
                "user_type": user_type,
                "marked_by": marked_by,
                "marked_by_type": marked_by_type,
                "attendance_date": attendance_date,
                "attendance_time": datetime.utcnow(),
                **attendance_data
            }
            
            attendance = await self.create(attendance_record)
            
            # Trigger alerts if needed
            await self._check_and_create_alerts(attendance)
            
            return attendance
    
    async def _validate_marking_permissions(
        self, 
        marked_by: UUID, 
        marked_by_type: UserType, 
        user_id: UUID, 
        user_type: UserType
    ) -> bool:
        """Validate if the marker has permission to mark attendance for the user"""
        
        # School authorities can mark anyone's attendance
        if marked_by_type == UserType.SCHOOL_AUTHORITY:
            return True
        
        # Teachers can mark student attendance and their own attendance
        if marked_by_type == UserType.TEACHER:
            if user_type == UserType.STUDENT:
                # Check if teacher is assigned to student's class
                return await self._verify_teacher_student_relationship(marked_by, user_id)
            elif user_type == UserType.TEACHER and marked_by == user_id:
                # Teachers can mark their own attendance
                return True
            else:
                return False
        
        # Students can only mark their own attendance (if allowed by policy)
        if marked_by_type == UserType.STUDENT:
            return marked_by == user_id and user_type == UserType.STUDENT
        
        return False
    
    async def _verify_teacher_student_relationship(self, teacher_id: UUID, student_id: UUID) -> bool:
        """Verify if teacher has permission to mark attendance for this student"""
        # This would check if teacher teaches any class that the student is enrolled in
        # Implementation depends on your class-teacher-student relationship model
        
        verify_sql = text("""
            SELECT COUNT(*) > 0
            FROM enrollments e
            JOIN classes c ON e.class_id = c.id
            JOIN class_subjects cs ON c.id = cs.class_id
            WHERE e.student_id = :student_id
            AND cs.teacher_id = :teacher_id
            AND e.status = 'active'
            AND e.is_deleted = false
            AND cs.is_active = true
        """)
        
        result = await self.db.execute(verify_sql, {
            "student_id": student_id,
            "teacher_id": teacher_id
        })
        
        return result.scalar() or False
    
    async def _get_existing_attendance(
        self, 
        user_id: UUID, 
        attendance_date: date, 
        attendance_type: AttendanceType,
        period_number: Optional[int] = None
    ) -> Optional[Attendance]:
        """Get existing attendance record"""
        
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.attendance_date == attendance_date,
            self.model.attendance_type == attendance_type,
            self.model.is_deleted == False
        )
        
        if period_number is not None:
            stmt = stmt.where(self.model.period_number == period_number)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    # BULK OPERATIONS USING RAW SQL FOR HIGH PERFORMANCE
    
    async def bulk_mark_attendance(self, attendance_records: List[dict], tenant_id: UUID) -> dict:
        """Bulk mark attendance using raw SQL for maximum performance"""
        try:
            if not attendance_records:
                raise HTTPException(status_code=400, detail="No attendance records provided")
            
            # Validate and prepare bulk insert data
            now = datetime.utcnow()
            today = date.today()
            insert_data = []
            validation_errors = []
            
            for idx, record in enumerate(attendance_records):
                try:
                    # Validate required fields
                    required_fields = ["user_id", "user_type", "marked_by", "marked_by_type"]
                    for field in required_fields:
                        if not record.get(field):
                            validation_errors.append(f"Row {idx + 1}: Missing required field '{field}'")
                            continue
                    
                    if validation_errors:
                        continue
                    
                    # Prepare attendance record
                    attendance_record = {
                        "id": str(uuid.uuid4()),
                        "tenant_id": str(tenant_id),
                        "user_id": str(record["user_id"]),
                        "user_type": record["user_type"],
                        "marked_by": str(record["marked_by"]),
                        "marked_by_type": record["marked_by_type"],
                        "class_id": str(record["class_id"]) if record.get("class_id") else None,
                        "attendance_date": record.get("attendance_date", today),
                        "attendance_time": now,
                        "attendance_type": record.get("attendance_type", "daily"),
                        "attendance_mode": record.get("attendance_mode", "manual"),
                        "status": record.get("status", "present"),
                        "check_in_time": record.get("check_in_time"),
                        "check_out_time": record.get("check_out_time"),
                        "period_number": record.get("period_number"),
                        "subject_name": record.get("subject_name"),
                        "location": record.get("location"),
                        "remarks": record.get("remarks"),
                        "reason_for_absence": record.get("reason_for_absence"),
                        "academic_year": record.get("academic_year", "2025-26"),
                        "term": record.get("term"),
                        "batch_id": str(uuid.uuid4()),  # Same batch for all records
                        "import_source": "bulk_upload",
                        "created_at": now,
                        "updated_at": now,
                        "is_deleted": False
                    }
                    insert_data.append(attendance_record)
                    
                except Exception as e:
                    validation_errors.append(f"Row {idx + 1}: {str(e)}")
            
            if validation_errors:
                raise HTTPException(
                    status_code=400, 
                    detail={"message": "Validation errors found", "errors": validation_errors}
                )
            
            # Bulk insert using raw SQL with conflict resolution
            bulk_insert_sql = text("""
                INSERT INTO attendances (
                    id, tenant_id, user_id, user_type, marked_by, marked_by_type,
                    class_id, attendance_date, attendance_time, attendance_type,
                    attendance_mode, status, check_in_time, check_out_time,
                    period_number, subject_name, location, remarks, reason_for_absence,
                    academic_year, term, batch_id, import_source, created_at, updated_at, is_deleted
                ) VALUES (
                    :id, :tenant_id, :user_id, :user_type, :marked_by, :marked_by_type,
                    :class_id, :attendance_date, :attendance_time, :attendance_type,
                    :attendance_mode, :status, :check_in_time, :check_out_time,
                    :period_number, :subject_name, :location, :remarks, :reason_for_absence,
                    :academic_year, :term, :batch_id, :import_source, :created_at, :updated_at, :is_deleted
                ) ON CONFLICT (user_id, attendance_date, attendance_type, period_number) 
                DO UPDATE SET
                    status = EXCLUDED.status,
                    marked_by = EXCLUDED.marked_by,
                    marked_by_type = EXCLUDED.marked_by_type,
                    attendance_time = EXCLUDED.attendance_time,
                    updated_at = EXCLUDED.updated_at
            """)
            
            await self.db.execute(bulk_insert_sql, insert_data)
            await self.db.commit()
            
            return {
                "total_records_processed": len(attendance_records),
                "successful_records": len(insert_data),
                "failed_records": len(validation_errors),
                "batch_id": insert_data[0]["batch_id"] if insert_data else None,
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk attendance marking failed: {str(e)}")
    
    async def bulk_update_attendance_status(self, attendance_ids: List[UUID], new_status: str, updated_by: UUID) -> dict:
        """Bulk update attendance status using raw SQL"""
        try:
            if not attendance_ids:
                raise HTTPException(status_code=400, detail="No attendance IDs provided")
            
            valid_statuses = [status.value for status in AttendanceStatus]
            if new_status not in valid_statuses:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid status. Must be one of: {valid_statuses}"
                )
            
            update_sql = text("""
                UPDATE attendances
                SET status = :new_status,
                    updated_at = :updated_at
                WHERE id = ANY(:attendance_ids)
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                update_sql,
                {
                    "new_status": new_status,
                    "updated_at": datetime.utcnow(),
                    "attendance_ids": [str(aid) for aid in attendance_ids]
                }
            )
            
            await self.db.commit()
            
            return {
                "updated_records": result.rowcount,
                "new_status": new_status,
                "updated_by": str(updated_by),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk status update failed: {str(e)}")
    
    async def bulk_approve_absences(self, attendance_ids: List[UUID], approved_by: UUID, approval_remarks: str = None) -> dict:
        """Bulk approve absences using raw SQL"""
        try:
            if not attendance_ids:
                raise HTTPException(status_code=400, detail="No attendance IDs provided")
            
            approve_sql = text("""
                UPDATE attendances
                SET is_excused = true,
                    approved_by = :approved_by,
                    approval_date = :approval_date,
                    approval_remarks = :approval_remarks,
                    updated_at = :updated_at
                WHERE id = ANY(:attendance_ids)
                AND status IN ('absent', 'sick')
                AND is_deleted = false
            """)
            
            now = datetime.utcnow()
            result = await self.db.execute(
                approve_sql,
                {
                    "approved_by": approved_by,
                    "approval_date": now,
                    "approval_remarks": approval_remarks,
                    "updated_at": now,
                    "attendance_ids": [str(aid) for aid in attendance_ids]
                }
            )
            
            await self.db.commit()
            
            return {
                "approved_records": result.rowcount,
                "approved_by": str(approved_by),
                "approval_date": now.isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk approval failed: {str(e)}")
    
    async def get_attendance_dashboard_stats(self, tenant_id: UUID, user_type: Optional[UserType] = None, date_range: Optional[dict] = None) -> dict:
        """Get comprehensive attendance dashboard statistics using raw SQL"""
        try:
            base_where = "WHERE a.tenant_id = :tenant_id AND a.is_deleted = false"
            params = {"tenant_id": tenant_id}
            
            if user_type:
                base_where += " AND a.user_type = :user_type"
                params["user_type"] = user_type.value
            
            if date_range:
                if date_range.get("start_date"):
                    base_where += " AND a.attendance_date >= :start_date"
                    params["start_date"] = date_range["start_date"]
                if date_range.get("end_date"):
                    base_where += " AND a.attendance_date <= :end_date"
                    params["end_date"] = date_range["end_date"]
            
            # Main statistics
            stats_sql = text(f"""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present_count,
                    COUNT(CASE WHEN a.status = 'absent' THEN 1 END) as absent_count,
                    COUNT(CASE WHEN a.status = 'late' THEN 1 END) as late_count,
                    COUNT(CASE WHEN a.status = 'excused' THEN 1 END) as excused_count,
                    COUNT(CASE WHEN a.status = 'sick' THEN 1 END) as sick_count,
                    COUNT(DISTINCT a.user_id) as unique_users,
                    COUNT(DISTINCT a.attendance_date) as unique_dates,
                    AVG(CASE WHEN a.status = 'present' THEN 100.0 ELSE 0.0 END) as avg_attendance_rate
                FROM attendances a
                {base_where}
            """)
            
            result = await self.db.execute(stats_sql, params)
            stats = result.fetchone()
            
            # Status distribution
            status_distribution_sql = text(f"""
                SELECT a.status, COUNT(*) as count
                FROM attendances a
                {base_where}
                GROUP BY a.status
                ORDER BY count DESC
            """)
            
            status_result = await self.db.execute(status_distribution_sql, params)
            status_distribution = {row[0]: row[1] for row in status_result.fetchall()}
            
            # Daily trends (last 30 days)
            daily_trends_sql = text(f"""
                SELECT 
                    a.attendance_date,
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present_count,
                    ROUND(AVG(CASE WHEN a.status = 'present' THEN 100.0 ELSE 0.0 END), 2) as attendance_rate
                FROM attendances a
                {base_where}
                AND a.attendance_date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY a.attendance_date
                ORDER BY a.attendance_date DESC
                LIMIT 30
            """)
            
            trends_result = await self.db.execute(daily_trends_sql, params)
            daily_trends = []
            for row in trends_result.fetchall():
                daily_trends.append({
                    "date": row[0].isoformat(),
                    "total_records": row[1],
                    "present_count": row[2],
                    "attendance_rate": float(row[3]) if row[3] else 0.0
                })
            
            # User type distribution
            user_type_sql = text(f"""
                SELECT a.user_type, COUNT(*) as count
                FROM attendances a
                {base_where}
                GROUP BY a.user_type
            """)
            
            user_type_result = await self.db.execute(user_type_sql, params)
            user_type_distribution = {row[0]: row[1] for row in user_type_result.fetchall()}
            
            return {
                "total_records": stats[0] or 0,
                "present_count": stats[1] or 0,
                "absent_count": stats[2] or 0,
                "late_count": stats[3] or 0,
                "excused_count": stats[4] or 0,
                "sick_count": stats[5] or 0,
                "unique_users": stats[6] or 0,
                "unique_dates": stats[7] or 0,
                "average_attendance_rate": round(float(stats[8]), 2) if stats[8] else 0.0,
                "overall_attendance_rate": round((stats[1] / stats[0] * 100), 2) if stats[0] > 0 else 0.0,
                "status_distribution": status_distribution,
                "user_type_distribution": user_type_distribution,
                "daily_trends": daily_trends,
                "tenant_id": str(tenant_id)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")
    
    async def get_low_attendance_users(self, tenant_id: UUID, threshold_percentage: int = 75, user_type: Optional[UserType] = None) -> List[dict]:
        """Get users with attendance below threshold using optimized SQL"""
        try:
            user_type_filter = ""
            params = {"tenant_id": tenant_id, "threshold": threshold_percentage}
            
            if user_type:
                user_type_filter = "AND a.user_type = :user_type"
                params["user_type"] = user_type.value
            
            low_attendance_sql = text(f"""
                SELECT 
                    a.user_id,
                    a.user_type,
                    COUNT(*) as total_days,
                    COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present_days,
                    ROUND(
                        (COUNT(CASE WHEN a.status = 'present' THEN 1 END)::float / COUNT(*)::float * 100), 
                        2
                    ) as attendance_percentage,
                    MAX(a.attendance_date) as last_attendance_date
                FROM attendances a
                WHERE a.tenant_id = :tenant_id
                AND a.is_deleted = false
                AND a.attendance_date >= CURRENT_DATE - INTERVAL '30 days'
                {user_type_filter}
                GROUP BY a.user_id, a.user_type
                HAVING ROUND(
                    (COUNT(CASE WHEN a.status = 'present' THEN 1 END)::float / COUNT(*)::float * 100), 
                    2
                ) < :threshold
                ORDER BY attendance_percentage ASC
            """)
            
            result = await self.db.execute(low_attendance_sql, params)
            
            low_attendance_users = []
            for row in result.fetchall():
                low_attendance_users.append({
                    "user_id": str(row[0]),
                    "user_type": row[1],
                    "total_days": row[2],
                    "present_days": row[3],
                    "attendance_percentage": float(row[4]),
                    "last_attendance_date": row[5].isoformat()
                })
            
            return low_attendance_users
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get low attendance users: {str(e)}")
    
    async def _check_and_create_alerts(self, attendance: Attendance):
        """Check if attendance triggers any alerts"""
        # Implementation for creating attendance alerts
        # This would check policies and create alerts for consecutive absences, low attendance, etc.
        pass
    
    # EXISTING METHODS (updated for async and role-based permissions)
    
    async def get_user_attendance(
        self, 
        user_id: UUID,
        user_type: UserType,
        requester_id: UUID,
        requester_type: UserType,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        attendance_type: Optional[AttendanceType] = None
    ) -> List[Attendance]:
        """Get attendance records for a user with permission validation"""
        
        # Validate permissions to view attendance
        if not await self._validate_view_permissions(requester_id, requester_type, user_id, user_type):
            raise HTTPException(status_code=403, detail="Insufficient permissions to view attendance")
        
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.user_type == user_type,
            self.model.is_deleted == False
        )
        
        if start_date:
            stmt = stmt.where(self.model.attendance_date >= start_date)
        if end_date:
            stmt = stmt.where(self.model.attendance_date <= end_date)
        if attendance_type:
            stmt = stmt.where(self.model.attendance_type == attendance_type)
        
        stmt = stmt.order_by(desc(self.model.attendance_date))
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def _validate_view_permissions(
        self, 
        requester_id: UUID, 
        requester_type: UserType, 
        user_id: UUID, 
        user_type: UserType
    ) -> bool:
        """Validate if the requester has permission to view attendance for the user"""
        
        # School authorities can view anyone's attendance
        if requester_type == UserType.SCHOOL_AUTHORITY:
            return True
        
        # Users can view their own attendance
        if requester_id == user_id and requester_type == user_type:
            return True
        
        # Teachers can view their students' attendance
        if requester_type == UserType.TEACHER and user_type == UserType.STUDENT:
            return await self._verify_teacher_student_relationship(requester_id, user_id)
        
        return False
