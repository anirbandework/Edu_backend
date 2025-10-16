from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, time, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy import and_, or_, func
from .base_service import BaseService
from ..models.tenant_specific.timetable import (
    MasterTimetable, Period, ClassTimetable, TeacherTimetable, 
    ScheduleEntry, TimetableConflict, DayOfWeek, PeriodType, TimetableStatus
)

class TimetableService(BaseService[MasterTimetable]):
    async def __init__(self, db: Session):
        super().__init__(MasterTimetable, db)
    
    async def create_master_timetable(self, timetable_data: dict) -> MasterTimetable:
        """Create a new master timetable with periods"""
        # Create master timetable
        master_timetable = self.create(timetable_data)
        
        # Auto-generate periods if not provided
        if not timetable_data.get("skip_period_generation", False):
            self._generate_default_periods(master_timetable)
        
        return master_timetable
    
    async def _generate_default_periods(self, master_timetable: MasterTimetable):
        """Generate default periods for a master timetable"""
        periods_data = []
        current_time = master_timetable.school_start_time
        
        # Convert time to datetime for calculations
        base_date = datetime.combine(date.today(), current_time)
        
        for i in range(master_timetable.total_periods_per_day):
            period_start = (base_date + timedelta(minutes=i * (master_timetable.period_duration + 5))).time()
            period_end = (base_date + timedelta(minutes=(i + 1) * master_timetable.period_duration + i * 5)).time()
            
            # Add breaks
            if i == 2:  # Morning break after 3rd period
                break_period = Period(
                    tenant_id=master_timetable.tenant_id,
                    master_timetable_id=master_timetable.id,
                    period_number=i + 0.5,
                    period_name="Morning Break",
                    period_type=PeriodType.BREAK,
                    start_time=period_end,
                    end_time=(datetime.combine(date.today(), period_end) + timedelta(minutes=15)).time(),
                    duration_minutes=15
                )
                self.db.add(break_period)
            
            if i == 5:  # Lunch break after 6th period  
                lunch_period = Period(
                    tenant_id=master_timetable.tenant_id,
                    master_timetable_id=master_timetable.id,
                    period_number=i + 0.5,
                    period_name="Lunch Break",
                    period_type=PeriodType.LUNCH,
                    start_time=period_end,
                    end_time=(datetime.combine(date.today(), period_end) + timedelta(minutes=60)).time(),
                    duration_minutes=60
                )
                self.db.add(lunch_period)
            
            period = Period(
                tenant_id=master_timetable.tenant_id,
                master_timetable_id=master_timetable.id,
                period_number=i + 1,
                period_name=f"Period {i + 1}",
                period_type=PeriodType.REGULAR,
                start_time=period_start,
                end_time=period_end,
                duration_minutes=master_timetable.period_duration
            )
            self.db.add(period)
        
        self.db.commit()
    
    async def create_class_timetable(self, class_timetable_data: dict) -> ClassTimetable:
        """Create timetable for a specific class"""
        class_timetable = ClassTimetable(**class_timetable_data)
        self.db.add(class_timetable)
        self.db.commit()
        self.db.refresh(class_timetable)
        return class_timetable
    
    async def create_teacher_timetable(self, teacher_timetable_data: dict) -> TeacherTimetable:
        """Create timetable for a specific teacher"""
        teacher_timetable = TeacherTimetable(**teacher_timetable_data)
        self.db.add(teacher_timetable)
        self.db.commit()
        self.db.refresh(teacher_timetable)
        return teacher_timetable
    
    async def add_schedule_entry(self, schedule_data: dict) -> ScheduleEntry:
        """Add a schedule entry and check for conflicts"""
        # Check for conflicts before adding
        conflicts = self._check_conflicts(schedule_data)
        
        if conflicts:
            # Log conflicts but still create entry
            for conflict in conflicts:
                self._create_conflict_record(conflict)
        
        schedule_entry = ScheduleEntry(**schedule_data)
        self.db.add(schedule_entry)
        self.db.commit()
        self.db.refresh(schedule_entry)
        
        return schedule_entry
    
    async def _check_conflicts(self, schedule_data: dict) -> List[Dict[str, Any]]:
        """Check for scheduling conflicts"""
        conflicts = []
        
        # Teacher double booking
        if schedule_data.get("teacher_timetable_id"):
            teacher_conflict = self.await db.execute(select(ScheduleEntry).filter(
                and_(
                    ScheduleEntry.teacher_timetable_id == schedule_data["teacher_timetable_id"],
                    ScheduleEntry.day_of_week == schedule_data["day_of_week"],
                    ScheduleEntry.period_id == schedule_data["period_id"],
                    ScheduleEntry.is_active == True
                )
            ).first()
            
            if teacher_conflict:
                conflicts.append({
                    "type": "teacher_double_booking",
                    "severity": "high",
                    "description": f"Teacher is already scheduled for this period",
                    "existing_entry_id": teacher_conflict.id
                })
        
        # Room conflict
        if schedule_data.get("room_number"):
            room_conflict = self.await db.execute(select(ScheduleEntry).filter(
                and_(
                    ScheduleEntry.room_number == schedule_data["room_number"],
                    ScheduleEntry.day_of_week == schedule_data["day_of_week"],
                    ScheduleEntry.period_id == schedule_data["period_id"],
                    ScheduleEntry.is_active == True
                )
            ).first()
            
            if room_conflict:
                conflicts.append({
                    "type": "room_conflict",
                    "severity": "medium",
                    "description": f"Room {schedule_data['room_number']} is already booked",
                    "existing_entry_id": room_conflict.id
                })
        
        return conflicts
    
    async def _create_conflict_record(self, conflict_data: dict):
        """Create a conflict record"""
        conflict = TimetableConflict(
            tenant_id=conflict_data.get("tenant_id"),
            conflict_type=conflict_data["type"],
            severity=conflict_data["severity"],
            description=conflict_data["description"]
        )
        self.db.add(conflict)
        self.db.commit()
    
    async def get_class_timetable(self, class_id: UUID, academic_year: str) -> Optional[ClassTimetable]:
        """Get timetable for a specific class"""
        return self.await db.execute(select(ClassTimetable).filter(
            and_(
                ClassTimetable.class_id == class_id,
                ClassTimetable.academic_year == academic_year,
                ClassTimetable.is_active == True,
                ClassTimetable.is_deleted == False
            )
        ).first()
    
    async def get_teacher_timetable(self, teacher_id: UUID, academic_year: str) -> Optional[TeacherTimetable]:
        """Get timetable for a specific teacher"""
        return self.await db.execute(select(TeacherTimetable).filter(
            and_(
                TeacherTimetable.teacher_id == teacher_id,
                TeacherTimetable.academic_year == academic_year,
                TeacherTimetable.is_active == True,
                TeacherTimetable.is_deleted == False
            )
        ).first()
    
    async def get_daily_schedule(
        self,
        class_timetable_id: UUID,
        day_of_week: DayOfWeek
    ) -> List[ScheduleEntry]:
        """Get daily schedule for a class"""
        return self.await db.execute(select(ScheduleEntry).join(Period).filter(
            and_(
                ScheduleEntry.class_timetable_id == class_timetable_id,
                ScheduleEntry.day_of_week == day_of_week,
                ScheduleEntry.is_active == True,
                ScheduleEntry.is_deleted == False
            )
        ).order_by(Period.period_number).all()
    
    async def get_weekly_schedule(self, class_timetable_id: UUID) -> Dict[str, List[ScheduleEntry]]:
        """Get weekly schedule for a class"""
        weekly_schedule = {}
        
        for day in DayOfWeek:
            daily_entries = self.get_daily_schedule(class_timetable_id, day)
            weekly_schedule[day.value] = daily_entries
        
        return weekly_schedule
    
    async def get_teacher_daily_schedule(
        self,
        teacher_timetable_id: UUID,
        day_of_week: DayOfWeek
    ) -> List[ScheduleEntry]:
        """Get daily schedule for a teacher"""
        return self.await db.execute(select(ScheduleEntry).join(Period).filter(
            and_(
                ScheduleEntry.teacher_timetable_id == teacher_timetable_id,
                ScheduleEntry.day_of_week == day_of_week,
                ScheduleEntry.is_active == True,
                ScheduleEntry.is_deleted == False
            )
        ).order_by(Period.period_number).all()
    
    async def get_conflicts(self, tenant_id: UUID, unresolved_only: bool = True) -> List[TimetableConflict]:
        """Get timetable conflicts"""
        query = self.await db.execute(select(TimetableConflict).filter(
            TimetableConflict.tenant_id == tenant_id,
            TimetableConflict.is_deleted == False
        )
        
        if unresolved_only:
            query = query.filter(TimetableConflict.is_resolved == False)
        
        return query.all()
    
    async def resolve_conflict(
        self,
        conflict_id: UUID,
        resolved_by: UUID,
        resolution_notes: str
    ) -> Optional[TimetableConflict]:
        """Resolve a timetable conflict"""
        conflict = self.await db.execute(select(TimetableConflict).filter(
            TimetableConflict.id == conflict_id
        ).first()
        
        if conflict:
            conflict.is_resolved = True
            conflict.resolved_by = resolved_by
            conflict.resolved_date = datetime.utcnow()
            conflict.resolution_notes = resolution_notes
            self.db.commit()
            self.db.refresh(conflict)
        
        return conflict
    
    async def get_room_utilization(
        self,
        tenant_id: UUID,
        room_number: str,
        academic_year: str
    ) -> Dict[str, Any]:
        """Get room utilization statistics"""
        total_slots = self.await db.execute(select(ScheduleEntry).join(Period).filter(
            ScheduleEntry.tenant_id == tenant_id,
            ScheduleEntry.room_number == room_number,
            ScheduleEntry.is_active == True
        ).count()
        
        # Calculate utilization percentage based on total possible slots
        total_possible_slots = 5 * 8  # 5 days * 8 periods (example)
        utilization_percentage = (total_slots / total_possible_slots) * 100 if total_possible_slots > 0 else 0
        
        return {
            "room_number": room_number,
            "total_scheduled_slots": total_slots,
            "total_possible_slots": total_possible_slots,
            "utilization_percentage": round(utilization_percentage, 2)
        }
    
    async def get_teacher_workload(
        self,
        teacher_id: UUID,
        academic_year: str
    ) -> Dict[str, Any]:
        """Get teacher workload statistics"""
        teacher_timetable = self.get_teacher_timetable(teacher_id, academic_year)
        
        if not teacher_timetable:
            return {"error": "Teacher timetable not found"}
        
        total_periods = self.await db.execute(select(ScheduleEntry).filter(
            ScheduleEntry.teacher_timetable_id == teacher_timetable.id,
            ScheduleEntry.is_active == True
        ).count()
        
        return {
            "teacher_id": str(teacher_id),
            "total_periods_per_week": total_periods,
            "max_periods_per_day": teacher_timetable.max_periods_per_day,
            "academic_year": academic_year
        }
