from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy import func, and_, or_
from .base_service import BaseService
from ..models.tenant_specific.attendance import Attendance, AttendanceSummary, AttendancePolicy, AttendanceStatus, AttendanceType

class AttendanceService(BaseService[Attendance]):
    async def __init__(self, db: Session):
        super().__init__(Attendance, db)
    
    async def mark_attendance(self, attendance_data: dict) -> Attendance:
        """Mark attendance for a student"""
        # Check if attendance already exists for the date
        existing = self.await db.execute(select(self.model).filter(
            self.model.student_id == attendance_data.get("student_id"),
            self.model.date == attendance_data.get("date"),
            self.model.attendance_type == attendance_data.get("attendance_type", AttendanceType.DAILY),
            self.model.period_number == attendance_data.get("period_number"),
            self.model.is_deleted == False
        ).first()
        
        if existing:
            # Update existing attendance
            for key, value in attendance_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new attendance record
            return self.create(attendance_data)
    
    async def get_student_attendance(
        self, 
        student_id: UUID, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        attendance_type: Optional[AttendanceType] = None
    ) -> List[Attendance]:
        """Get attendance records for a student"""
        query = self.await db.execute(select(self.model).filter(
            self.model.student_id == student_id,
            self.model.is_deleted == False
        )
        
        if start_date:
            query = query.filter(func.date(self.model.date) >= start_date)
        if end_date:
            query = query.filter(func.date(self.model.date) <= end_date)
        if attendance_type:
            query = query.filter(self.model.attendance_type == attendance_type)
        
        return query.order_by(self.model.date.desc()).all()
    
    async def get_class_attendance(
        self,
        class_id: UUID,
        attendance_date: date,
        period_number: Optional[int] = None
    ) -> List[Attendance]:
        """Get attendance for all students in a class for a specific date"""
        query = self.await db.execute(select(self.model).filter(
            self.model.class_id == class_id,
            func.date(self.model.date) == attendance_date,
            self.model.is_deleted == False
        )
        
        if period_number:
            query = query.filter(self.model.period_number == period_number)
        
        return query.all()
    
    async def get_attendance_statistics(
        self,
        student_id: Optional[UUID] = None,
        class_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Generate attendance statistics"""
        query = self.await db.execute(select(self.model).filter(self.model.is_deleted == False)
        
        if student_id:
            query = query.filter(self.model.student_id == student_id)
        if class_id:
            query = query.filter(self.model.class_id == class_id)
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
        if start_date:
            query = query.filter(func.date(self.model.date) >= start_date)
        if end_date:
            query = query.filter(func.date(self.model.date) <= end_date)
        
        # Get counts by status
        stats = {}
        for status in AttendanceStatus:
            count = query.filter(self.model.status == status).count()
            stats[status.value] = count
        
        total_records = sum(stats.values())
        
        # Calculate percentages
        if total_records > 0:
            stats["attendance_percentage"] = round((stats.get("present", 0) / total_records) * 100, 2)
            stats["absence_percentage"] = round((stats.get("absent", 0) / total_records) * 100, 2)
        else:
            stats["attendance_percentage"] = 0
            stats["absence_percentage"] = 0
        
        stats["total_records"] = total_records
        return stats
    
    async def get_low_attendance_students(
        self,
        tenant_id: UUID,
        threshold_percentage: int = 75,
        academic_year: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get students with attendance below threshold"""
        # This would typically use AttendanceSummary table for better performance
        # For now, calculating on the fly
        query = self.await db.execute(select(self.model.student_id, func.count().label('total'), 
                             func.sum(func.case([(self.model.status == AttendanceStatus.PRESENT, 1)], else_=0)).label('present')).filter(
            self.model.tenant_id == tenant_id,
            self.model.is_deleted == False
        )
        
        if academic_year:
            query = query.filter(self.model.academic_year == academic_year)
        
        results = query.group_by(self.model.student_id).all()
        
        low_attendance = []
        for result in results:
            if result.total > 0:
                percentage = (result.present / result.total) * 100
                if percentage < threshold_percentage:
                    low_attendance.append({
                        "student_id": str(result.student_id),
                        "total_days": result.total,
                        "present_days": result.present,
                        "attendance_percentage": round(percentage, 2)
                    })
        
        return low_attendance
    
    async def bulk_mark_attendance(self, attendance_records: List[dict]) -> List[Attendance]:
        """Mark attendance for multiple students at once"""
        created_records = []
        for record in attendance_records:
            try:
                attendance = self.mark_attendance(record)
                created_records.append(attendance)
            except Exception as e:
                # Log error but continue with other records
                print(f"Error marking attendance for record {record}: {str(e)}")
                continue
        
        return created_records
    
    async def get_absent_students_today(self, tenant_id: UUID, class_id: Optional[UUID] = None) -> List[Attendance]:
        """Get students who are absent today"""
        today = date.today()
        query = self.await db.execute(select(self.model).filter(
            self.model.tenant_id == tenant_id,
            func.date(self.model.date) == today,
            self.model.status == AttendanceStatus.ABSENT,
            self.model.is_deleted == False
        )
        
        if class_id:
            query = query.filter(self.model.class_id == class_id)
        
        return query.all()
    
    async def get_monthly_attendance_summary(
        self,
        student_id: UUID,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        """Get monthly attendance summary for a student"""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        return self.get_attendance_statistics(
            student_id=student_id,
            start_date=start_date,
            end_date=end_date
        )
    
    async def approve_absence(
        self,
        attendance_id: UUID,
        approved_by: UUID,
        approval_remarks: Optional[str] = None
    ) -> Optional[Attendance]:
        """Approve an absence"""
        attendance = self.get(attendance_id)
        if attendance:
            attendance.is_excused = True
            attendance.approved_by = approved_by
            attendance.approval_date = datetime.utcnow()
            attendance.approval_remarks = approval_remarks
            self.db.commit()
            self.db.refresh(attendance)
        
        return attendance
