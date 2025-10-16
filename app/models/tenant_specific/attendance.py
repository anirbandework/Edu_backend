from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import BaseModel
import enum

class AttendanceStatus(enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"
    SICK = "sick"
    PARTIAL = "partial"

class AttendanceType(enum.Enum):
    DAILY = "daily"
    PERIOD = "period"
    EVENT = "event"
    EXAM = "exam"

class Attendance(BaseModel):
    __tablename__ = "attendances"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=True, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"), nullable=True, index=True)
    
    # Attendance Information
    date = Column(DateTime, nullable=False, index=True)
    attendance_type = Column(Enum(AttendanceType), default=AttendanceType.DAILY, nullable=False)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False)
    
    # Time Information
    check_in_time = Column(Time)
    check_out_time = Column(Time)
    expected_check_in = Column(Time)
    expected_check_out = Column(Time)
    
    # Additional Details
    period_number = Column(Integer)  # For period-wise attendance
    subject = Column(String(100))    # Subject name if period-wise
    remarks = Column(Text)
    reason_for_absence = Column(String(500))
    is_excused = Column(Boolean, default=False)
    
    # Approval Information
    approved_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"), nullable=True)
    approval_date = Column(DateTime)
    approval_remarks = Column(Text)
    
    # Academic Information
    academic_year = Column(String(10), nullable=False, index=True)
    term = Column(String(20))  # "Term 1", "Term 2", etc.
    week_number = Column(Integer)
    
    # Relationships
    tenant = relationship("Tenant")
    student = relationship("Student", back_populates="attendances")
    class_ref = relationship("ClassModel")
    teacher = relationship("Teacher")
    approved_by_authority = relationship("SchoolAuthority")

class AttendanceSummary(BaseModel):
    __tablename__ = "attendance_summaries"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=True, index=True)
    
    # Summary Period
    summary_type = Column(String(20), nullable=False)  # "monthly", "weekly", "term", "annual"
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    academic_year = Column(String(10), nullable=False)
    
    # Statistics
    total_days = Column(Integer, default=0)
    present_days = Column(Integer, default=0)
    absent_days = Column(Integer, default=0)
    late_days = Column(Integer, default=0)
    excused_days = Column(Integer, default=0)
    sick_days = Column(Integer, default=0)
    
    # Calculated Fields
    attendance_percentage = Column(Integer, default=0)  # 0-100
    
    # Last Updated
    last_calculated = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant")
    student = relationship("Student")
    class_ref = relationship("ClassModel")

class AttendancePolicy(BaseModel):
    __tablename__ = "attendance_policies"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Policy Information
    policy_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Time Rules
    school_start_time = Column(Time, nullable=False)
    school_end_time = Column(Time, nullable=False)
    late_threshold_minutes = Column(Integer, default=15)  # Minutes after start time
    
    # Attendance Rules
    minimum_attendance_percentage = Column(Integer, default=75)  # Required percentage
    consecutive_absent_alert = Column(Integer, default=3)  # Alert after N consecutive absences
    monthly_absent_limit = Column(Integer, default=5)  # Maximum absences per month
    
    # Grace Periods
    grace_period_minutes = Column(Integer, default=5)  # Grace period for late arrival
    early_departure_threshold = Column(Integer, default=30)  # Minutes before end time
    
    # Notification Rules
    notify_parents_after_days = Column(Integer, default=1)
    notify_administration_after_days = Column(Integer, default=3)
    
    # Academic Year
    academic_year = Column(String(10), nullable=False)
    effective_from = Column(DateTime, nullable=False)
    effective_until = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant")
