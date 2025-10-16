from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from ..base import BaseModel
import enum

class DayOfWeek(enum.Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

class PeriodType(enum.Enum):
    REGULAR = "regular"
    BREAK = "break"
    LUNCH = "lunch"
    ASSEMBLY = "assembly"
    SPORTS = "sports"
    LIBRARY = "library"
    LAB = "lab"
    EXAM = "exam"

class TimetableStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

class MasterTimetable(BaseModel):
    __tablename__ = "master_timetables"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Timetable Information
    timetable_name = Column(String(100), nullable=False)
    description = Column(Text)
    academic_year = Column(String(10), nullable=False, index=True)
    term = Column(String(20))  # "Term 1", "Semester 1", etc.
    
    # Schedule Details
    effective_from = Column(Date, nullable=False)
    effective_until = Column(Date)
    total_periods_per_day = Column(Integer, default=8)
    
    # Timing Configuration
    school_start_time = Column(Time, nullable=False)
    school_end_time = Column(Time, nullable=False)
    period_duration = Column(Integer, default=45)  # minutes
    break_duration = Column(Integer, default=15)   # minutes
    lunch_duration = Column(Integer, default=60)   # minutes
    
    # Working Days
    working_days = Column(JSON)  # ["monday", "tuesday", ...]
    
    # Status
    status = Column(Enum(TimetableStatus), default=TimetableStatus.DRAFT, nullable=False)
    is_default = Column(Boolean, default=False)
    
    # Relationships
    tenant = relationship("Tenant")
    class_timetables = relationship("ClassTimetable", back_populates="master_timetable", cascade="all, delete-orphan")
    teacher_timetables = relationship("TeacherTimetable", back_populates="master_timetable", cascade="all, delete-orphan")

class Period(BaseModel):
    __tablename__ = "periods"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    master_timetable_id = Column(UUID(as_uuid=True), ForeignKey("master_timetables.id"), nullable=False, index=True)
    
    # Period Information
    period_number = Column(Integer, nullable=False)
    period_name = Column(String(50))  # "Period 1", "Morning Break", etc.
    period_type = Column(Enum(PeriodType), default=PeriodType.REGULAR, nullable=False)
    
    # Timing
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    
    # Additional Information
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant")
    master_timetable = relationship("MasterTimetable")
    schedule_entries = relationship("ScheduleEntry", back_populates="period")

class ClassTimetable(BaseModel):
    __tablename__ = "class_timetables"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False, index=True)
    master_timetable_id = Column(UUID(as_uuid=True), ForeignKey("master_timetables.id"), nullable=False, index=True)
    
    # Timetable Information
    academic_year = Column(String(10), nullable=False)
    term = Column(String(20))
    
    # Status
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    approval_date = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant")
    class_ref = relationship("ClassModel")
    master_timetable = relationship("MasterTimetable", back_populates="class_timetables")
    schedule_entries = relationship("ScheduleEntry", back_populates="class_timetable")
    created_by_authority = relationship("SchoolAuthority", foreign_keys=[created_by])
    approved_by_authority = relationship("SchoolAuthority", foreign_keys=[approved_by])

class TeacherTimetable(BaseModel):
    __tablename__ = "teacher_timetables"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"), nullable=False, index=True)
    master_timetable_id = Column(UUID(as_uuid=True), ForeignKey("master_timetables.id"), nullable=False, index=True)
    
    # Timetable Information
    academic_year = Column(String(10), nullable=False)
    term = Column(String(20))
    
    # Teaching Load
    total_periods_per_week = Column(Integer, default=0)
    max_periods_per_day = Column(Integer, default=8)
    preferred_periods = Column(JSON)  # Teacher preferences
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant")
    teacher = relationship("Teacher")
    master_timetable = relationship("MasterTimetable", back_populates="teacher_timetables")
    schedule_entries = relationship("ScheduleEntry", back_populates="teacher_timetable")

class ScheduleEntry(BaseModel):
    __tablename__ = "schedule_entries"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    class_timetable_id = Column(UUID(as_uuid=True), ForeignKey("class_timetables.id"), nullable=False, index=True)
    teacher_timetable_id = Column(UUID(as_uuid=True), ForeignKey("teacher_timetables.id"), nullable=True, index=True)
    period_id = Column(UUID(as_uuid=True), ForeignKey("periods.id"), nullable=False, index=True)
    
    # Schedule Information
    day_of_week = Column(Enum(DayOfWeek), nullable=False, index=True)
    subject_name = Column(String(100), nullable=False)
    subject_code = Column(String(20))
    
    # Location
    room_number = Column(String(20))
    building = Column(String(50))
    location_notes = Column(Text)
    
    # Additional Information
    notes = Column(Text)
    is_substitution = Column(Boolean, default=False)
    original_teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"))
    substitution_reason = Column(String(200))
    
    # Special Configurations
    is_recurring = Column(Boolean, default=True)
    effective_date = Column(Date)
    expiry_date = Column(Date)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant")
    class_timetable = relationship("ClassTimetable", back_populates="schedule_entries")
    teacher_timetable = relationship("TeacherTimetable", back_populates="schedule_entries")
    period = relationship("Period", back_populates="schedule_entries")
    original_teacher = relationship("Teacher", foreign_keys=[original_teacher_id])

class TimetableConflict(BaseModel):
    __tablename__ = "timetable_conflicts"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Conflict Information
    conflict_type = Column(String(50), nullable=False)  # "teacher_double_booking", "room_conflict", etc.
    severity = Column(String(20), default="medium")  # "low", "medium", "high", "critical"
    description = Column(Text, nullable=False)
    
    # Related Entities
    schedule_entry_1_id = Column(UUID(as_uuid=True), ForeignKey("schedule_entries.id"))
    schedule_entry_2_id = Column(UUID(as_uuid=True), ForeignKey("schedule_entries.id"))
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"))
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"))
    
    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    resolved_date = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant")
    schedule_entry_1 = relationship("ScheduleEntry", foreign_keys=[schedule_entry_1_id])
    schedule_entry_2 = relationship("ScheduleEntry", foreign_keys=[schedule_entry_2_id])
    teacher = relationship("Teacher")
    class_ref = relationship("ClassModel")
    resolved_by_authority = relationship("SchoolAuthority")
