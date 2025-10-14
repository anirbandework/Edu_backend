# app/models/tenant_specific/timetable.py
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Time, Text, Enum, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from ..base import Base
import enum
from datetime import datetime


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
    ACTIVITY = "activity"
    STUDY_HALL = "study_hall"


class TimetableStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    PENDING_APPROVAL = "pending_approval"


class ConflictSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MasterTimetable(Base):
    __tablename__ = "master_timetables"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Timetable Information
    timetable_name = Column(String(100), nullable=False)
    description = Column(Text)
    academic_year = Column(String(10), nullable=False, index=True)
    term = Column(String(20))  # "Term 1", "Semester 1", etc.
    version = Column(String(10), default="1.0")
    
    # Schedule Details
    effective_from = Column(Date, nullable=False)
    effective_until = Column(Date)
    total_periods_per_day = Column(Integer, default=8)
    total_working_days = Column(Integer, default=5)
    
    # Timing Configuration
    school_start_time = Column(Time, nullable=False)
    school_end_time = Column(Time, nullable=False)
    period_duration = Column(Integer, default=45)  # minutes
    break_duration = Column(Integer, default=15)   # minutes
    lunch_duration = Column(Integer, default=60)   # minutes
    
    # Working Days Configuration
    working_days = Column(JSON)  # ["monday", "tuesday", ...]
    holidays = Column(JSON)      # List of holiday dates
    
    # Status and Approval
    status = Column(Enum(TimetableStatus), default=TimetableStatus.DRAFT, nullable=False)
    is_default = Column(Boolean, default=False)
    approved_by = Column(UUID(as_uuid=True))
    approved_at = Column(DateTime)
    
    # Generation Settings
    auto_generate_periods = Column(Boolean, default=True)
    conflict_check_enabled = Column(Boolean, default=True)
    
    # Statistics
    total_classes = Column(Integer, default=0)
    total_teachers = Column(Integer, default=0)
    total_schedule_entries = Column(Integer, default=0)
    
    # Relationships
    tenant = relationship("Tenant")
    periods = relationship("Period", back_populates="master_timetable", cascade="all, delete-orphan")
    class_timetables = relationship("ClassTimetable", back_populates="master_timetable", cascade="all, delete-orphan")
    teacher_timetables = relationship("TeacherTimetable", back_populates="master_timetable", cascade="all, delete-orphan")


class Period(Base):
    __tablename__ = "periods"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    master_timetable_id = Column(UUID(as_uuid=True), ForeignKey("master_timetables.id"), nullable=False, index=True)
    
    # Period Information
    period_number = Column(Integer, nullable=False)
    period_name = Column(String(50), nullable=False)  # "Period 1", "Morning Break", etc.
    period_type = Column(Enum(PeriodType), default=PeriodType.REGULAR, nullable=False)
    
    # Timing
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    
    # Configuration
    is_teaching_period = Column(Boolean, default=True)  # False for breaks
    allows_substitution = Column(Boolean, default=True)
    
    # Additional Information
    description = Column(Text)
    color_code = Column(String(7))  # Hex color for UI
    is_active = Column(Boolean, default=True)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('master_timetable_id', 'period_number', name='unique_period_per_timetable'),
    )
    
    # Relationships
    tenant = relationship("Tenant")
    master_timetable = relationship("MasterTimetable", back_populates="periods")
    schedule_entries = relationship("ScheduleEntry", back_populates="period")


class ClassTimetable(Base):
    __tablename__ = "class_timetables"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # References classes table
    master_timetable_id = Column(UUID(as_uuid=True), ForeignKey("master_timetables.id"), nullable=False, index=True)
    
    # Timetable Information
    academic_year = Column(String(10), nullable=False)
    term = Column(String(20))
    class_name = Column(String(100))  # Cache class name for quick access
    grade_level = Column(String(20))  # Cache grade level
    
    # Configuration
    total_subjects = Column(Integer, default=0)
    total_weekly_periods = Column(Integer, default=0)
    
    # Status and Approval
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True))
    approved_by = Column(UUID(as_uuid=True))
    approval_date = Column(DateTime)
    last_modified_by = Column(UUID(as_uuid=True))
    
    # Publishing
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('class_id', 'academic_year', 'term', name='unique_class_timetable'),
    )
    
    # Relationships
    tenant = relationship("Tenant")
    master_timetable = relationship("MasterTimetable", back_populates="class_timetables")
    schedule_entries = relationship("ScheduleEntry", back_populates="class_timetable", cascade="all, delete-orphan")


class TeacherTimetable(Base):
    __tablename__ = "teacher_timetables"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # References teachers table
    master_timetable_id = Column(UUID(as_uuid=True), ForeignKey("master_timetables.id"), nullable=False, index=True)
    
    # Timetable Information
    academic_year = Column(String(10), nullable=False)
    term = Column(String(20))
    teacher_name = Column(String(200))  # Cache teacher name
    
    # Teaching Load Configuration
    total_periods_per_week = Column(Integer, default=0)
    max_periods_per_day = Column(Integer, default=8)
    min_periods_per_day = Column(Integer, default=1)
    
    # Preferences
    preferred_periods = Column(JSON)  # Teacher period preferences
    preferred_days = Column(JSON)     # Teacher day preferences
    unavailable_slots = Column(JSON)  # Times when teacher is unavailable
    
    # Subject Specializations
    subjects = Column(JSON)  # List of subjects teacher can teach
    
    # Workload Statistics
    actual_periods_per_week = Column(Integer, default=0)
    free_periods_per_week = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    workload_percentage = Column(Integer, default=0)  # 0-100
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('teacher_id', 'academic_year', 'term', name='unique_teacher_timetable'),
    )
    
    # Relationships
    tenant = relationship("Tenant")
    master_timetable = relationship("MasterTimetable", back_populates="teacher_timetables")
    schedule_entries = relationship("ScheduleEntry", back_populates="teacher_timetable")


class Subject(Base):
    __tablename__ = "subjects"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Subject Information
    subject_name = Column(String(100), nullable=False)
    subject_code = Column(String(20), nullable=False)
    description = Column(Text)
    
    # Configuration
    grade_levels = Column(JSON)  # Which grades this subject is for
    subject_category = Column(String(50))  # "core", "elective", "activity"
    periods_per_week = Column(Integer, default=5)
    
    # Requirements
    requires_lab = Column(Boolean, default=False)
    requires_special_room = Column(Boolean, default=False)
    max_students_per_class = Column(Integer, default=35)
    
    # Status
    is_active = Column(Boolean, default=True)
    color_code = Column(String(7))  # Hex color for UI
    
    # Academic Information
    academic_year = Column(String(10), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
    schedule_entries = relationship("ScheduleEntry", back_populates="subject")


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    class_timetable_id = Column(UUID(as_uuid=True), ForeignKey("class_timetables.id"), nullable=False, index=True)
    teacher_timetable_id = Column(UUID(as_uuid=True), ForeignKey("teacher_timetables.id"), nullable=True, index=True)
    period_id = Column(UUID(as_uuid=True), ForeignKey("periods.id"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=True, index=True)
    
    # Schedule Information
    day_of_week = Column(Enum(DayOfWeek), nullable=False, index=True)
    
    # Subject Information (cached for performance)
    subject_name = Column(String(100), nullable=False)
    subject_code = Column(String(20))
    
    # Location Information
    room_number = Column(String(20))
    building = Column(String(50))
    floor = Column(String(10))
    location_notes = Column(Text)
    room_capacity = Column(Integer)
    
    # Teacher Information (cached for performance)
    teacher_name = Column(String(200))
    
    # Special Configurations
    is_recurring = Column(Boolean, default=True)
    effective_date = Column(Date)
    expiry_date = Column(Date)
    
    # Substitution Information
    is_substitution = Column(Boolean, default=False)
    original_teacher_id = Column(UUID(as_uuid=True))
    original_teacher_name = Column(String(200))
    substitution_reason = Column(String(200))
    substitution_date = Column(Date)
    
    # Additional Information
    notes = Column(Text)
    attendance_required = Column(Boolean, default=True)
    
    # Batch Information (for bulk operations)
    batch_id = Column(UUID(as_uuid=True))
    import_source = Column(String(50))  # "manual", "bulk_import", "auto_generated"
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Unique constraint for regular schedules
    __table_args__ = (
        UniqueConstraint('class_timetable_id', 'day_of_week', 'period_id', 
                        name='unique_class_day_period'),
    )
    
    # Relationships
    tenant = relationship("Tenant")
    class_timetable = relationship("ClassTimetable", back_populates="schedule_entries")
    teacher_timetable = relationship("TeacherTimetable", back_populates="schedule_entries")
    period = relationship("Period", back_populates="schedule_entries")
    subject = relationship("Subject", back_populates="schedule_entries")


class TimetableConflict(Base):
    __tablename__ = "timetable_conflicts"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Conflict Information
    conflict_type = Column(String(50), nullable=False)  # "teacher_double_booking", "room_conflict", etc.
    severity = Column(Enum(ConflictSeverity), default=ConflictSeverity.MEDIUM, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Related Entities
    schedule_entry_1_id = Column(UUID(as_uuid=True), ForeignKey("schedule_entries.id"))
    schedule_entry_2_id = Column(UUID(as_uuid=True), ForeignKey("schedule_entries.id"))
    teacher_id = Column(UUID(as_uuid=True))
    class_id = Column(UUID(as_uuid=True))
    room_number = Column(String(20))
    
    # Conflict Details
    day_of_week = Column(Enum(DayOfWeek))
    period_number = Column(Integer)
    conflict_data = Column(JSON)  # Additional conflict details
    
    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    resolution_action = Column(String(100))  # "reassign_teacher", "change_room", etc.
    resolved_by = Column(UUID(as_uuid=True))
    resolved_date = Column(DateTime)
    
    # Auto-detection
    detected_by = Column(String(50), default="system")  # "system", "manual"
    auto_resolve = Column(Boolean, default=False)
    
    # Relationships
    tenant = relationship("Tenant")
    schedule_entry_1 = relationship("ScheduleEntry", foreign_keys=[schedule_entry_1_id])
    schedule_entry_2 = relationship("ScheduleEntry", foreign_keys=[schedule_entry_2_id])


class TimetableTemplate(Base):
    __tablename__ = "timetable_templates"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    
    # Template Information
    template_name = Column(String(100), nullable=False)
    description = Column(Text)
    template_type = Column(String(50))  # "class", "teacher", "grade_level"
    
    # Template Configuration
    grade_levels = Column(JSON)  # Applicable grade levels
    template_data = Column(JSON)  # Template structure
    
    # Usage Statistics
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # Available to other schools
    
    # Relationships
    tenant = relationship("Tenant")


class TimetableAuditLog(Base):
    __tablename__ = "timetable_audit_logs"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Audit Information
    action_type = Column(String(50), nullable=False)  # "create", "update", "delete", "publish"
    entity_type = Column(String(50), nullable=False)  # "master_timetable", "schedule_entry", etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    
    # User Information
    performed_by = Column(UUID(as_uuid=True), nullable=False)
    performed_by_name = Column(String(200))
    user_role = Column(String(50))  # "school_authority", "teacher", etc.
    
    # Change Details
    old_values = Column(JSON)
    new_values = Column(JSON)
    change_description = Column(Text)
    
    # Context
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    session_id = Column(String(100))
    
    # Timing
    action_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
