from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from ..base import BaseModel
import enum

class AssessmentType(enum.Enum):
    QUIZ = "quiz"
    TEST = "test"
    EXAM = "exam"
    HOMEWORK = "homework"
    ASSIGNMENT = "assignment"
    PROJECT = "project"
    PRESENTATION = "presentation"
    LAB_WORK = "lab_work"
    PRACTICAL = "practical"
    MIDTERM = "midterm"
    FINAL = "final"

class GradingSystem(enum.Enum):
    PERCENTAGE = "percentage"         # 0-100
    LETTER_GRADE = "letter_grade"     # A, B, C, D, F
    GPA = "gpa"                      # 4.0 scale
    POINTS = "points"                # Raw points
    PASS_FAIL = "pass_fail"          # Pass/Fail

class AssessmentStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    GRADED = "graded"
    ARCHIVED = "archived"

class SubmissionStatus(enum.Enum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    LATE = "late"
    GRADED = "graded"
    RETURNED = "returned"

class Subject(BaseModel):
    __tablename__ = "subjects"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Subject Information
    subject_code = Column(String(20), nullable=False, index=True)
    subject_name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Academic Information
    department = Column(String(50))
    credit_hours = Column(Integer, default=3)
    academic_year = Column(String(10), nullable=False)
    
    # Grading Configuration
    grading_system = Column(Enum(GradingSystem), default=GradingSystem.PERCENTAGE)
    passing_grade = Column(Numeric(5, 2), default=60.00)
    max_grade = Column(Numeric(5, 2), default=100.00)
    
    # Component Weights (stored as JSON)
    grade_components = Column(JSON)  # {"quiz": 20, "homework": 30, "exam": 50}
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Management
    created_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    
    # Relationships
    tenant = relationship("Tenant")
    created_by_authority = relationship("SchoolAuthority")
    assessments = relationship("Assessment", back_populates="subject")
    class_subjects = relationship("ClassSubject", back_populates="subject")

class ClassSubject(BaseModel):
    __tablename__ = "class_subjects"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"), nullable=False, index=True)
    
    # Assignment Information
    academic_year = Column(String(10), nullable=False)
    term = Column(String(20))
    
    # Schedule Information
    periods_per_week = Column(Integer, default=5)
    total_periods = Column(Integer)
    
    # Custom Grading (if different from subject default)
    custom_grade_components = Column(JSON)
    custom_passing_grade = Column(Numeric(5, 2))
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant")
    class_ref = relationship("ClassModel")
    subject = relationship("Subject", back_populates="class_subjects")
    teacher = relationship("Teacher")
    student_grades = relationship("StudentGrade", back_populates="class_subject")

class Assessment(BaseModel):
    __tablename__ = "assessments"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"), nullable=False, index=True)
    
    # Assessment Information
    assessment_title = Column(String(200), nullable=False)
    assessment_code = Column(String(50), nullable=False)
    assessment_type = Column(Enum(AssessmentType), nullable=False)
    description = Column(Text)
    
    # Scheduling
    scheduled_date = Column(DateTime)
    due_date = Column(DateTime)
    duration_minutes = Column(Integer)  # For timed assessments
    
    # Grading Information
    max_marks = Column(Numeric(8, 2), nullable=False)
    passing_marks = Column(Numeric(8, 2))
    weightage = Column(Numeric(5, 2))  # Percentage weight in final grade
    
    # Instructions and Content
    instructions = Column(Text)
    assessment_content = Column(JSON)  # Questions, rubrics, etc.
    attachments = Column(JSON)  # File URLs
    
    # Settings
    allow_late_submission = Column(Boolean, default=False)
    late_penalty_percent = Column(Numeric(5, 2), default=0)
    attempts_allowed = Column(Integer, default=1)
    
    # Status and Timing
    status = Column(Enum(AssessmentStatus), default=AssessmentStatus.DRAFT)
    publish_date = Column(DateTime)
    auto_grade = Column(Boolean, default=False)
    
    # Academic Information
    academic_year = Column(String(10), nullable=False)
    term = Column(String(20))
    
    # Relationships
    tenant = relationship("Tenant")
    subject = relationship("Subject", back_populates="assessments")
    class_ref = relationship("ClassModel")
    teacher = relationship("Teacher")
    submissions = relationship("AssessmentSubmission", back_populates="assessment")

class AssessmentSubmission(BaseModel):
    __tablename__ = "assessment_submissions"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    
    # Submission Information
    submission_date = Column(DateTime)
    is_late = Column(Boolean, default=False)
    attempt_number = Column(Integer, default=1)
    
    # Content
    submission_content = Column(JSON)  # Answers, files, etc.
    attachments = Column(JSON)  # File URLs
    submission_notes = Column(Text)
    
    # Grading
    marks_obtained = Column(Numeric(8, 2))
    percentage = Column(Numeric(5, 2))
    grade_letter = Column(String(5))
    is_graded = Column(Boolean, default=False)
    
    # Feedback
    teacher_feedback = Column(Text)
    detailed_feedback = Column(JSON)  # Question-wise feedback
    graded_by = Column(UUID(as_uuid=True), ForeignKey("teachers.id"))
    graded_date = Column(DateTime)
    
    # Status
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.NOT_SUBMITTED)
    
    # Relationships
    tenant = relationship("Tenant")
    assessment = relationship("Assessment", back_populates="submissions")
    student = relationship("Student")
    graded_by_teacher = relationship("Teacher")

class StudentGrade(BaseModel):
    __tablename__ = "student_grades"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    class_subject_id = Column(UUID(as_uuid=True), ForeignKey("class_subjects.id"), nullable=False, index=True)
    
    # Academic Information
    academic_year = Column(String(10), nullable=False)
    term = Column(String(20))
    
    # Component Grades (stored as JSON for flexibility)
    component_grades = Column(JSON)  # {"quiz": 85, "homework": 90, "exam": 78}
    component_weights = Column(JSON)  # {"quiz": 20, "homework": 30, "exam": 50}
    
    # Final Calculations
    total_marks_obtained = Column(Numeric(8, 2))
    total_max_marks = Column(Numeric(8, 2))
    percentage = Column(Numeric(5, 2))
    letter_grade = Column(String(5))
    gpa = Column(Numeric(3, 2))
    
    # Status
    is_final = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    
    # Tracking
    last_updated = Column(DateTime)
    calculated_by = Column(UUID(as_uuid=True), ForeignKey("teachers.id"))
    
    # Comments
    teacher_comments = Column(Text)
    
    # Relationships
    tenant = relationship("Tenant")
    student = relationship("Student")
    class_subject = relationship("ClassSubject", back_populates="student_grades")
    calculated_by_teacher = relationship("Teacher")

class GradeScale(BaseModel):
    __tablename__ = "grade_scales"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Scale Information
    scale_name = Column(String(50), nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    
    # Scale Configuration (stored as JSON)
    grade_ranges = Column(JSON)  # [{"min": 90, "max": 100, "letter": "A", "gpa": 4.0}, ...]
    
    # Applicability
    applicable_subjects = Column(JSON)  # List of subject IDs
    academic_year = Column(String(10), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Management
    created_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    
    # Relationships
    tenant = relationship("Tenant")
    created_by_authority = relationship("SchoolAuthority")

class ReportCard(BaseModel):
    __tablename__ = "report_cards"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False, index=True)
    
    # Report Information
    report_period = Column(String(20), nullable=False)  # "Term 1", "Semester 1", etc.
    academic_year = Column(String(10), nullable=False)
    
    # Overall Performance
    total_subjects = Column(Integer)
    subjects_passed = Column(Integer)
    subjects_failed = Column(Integer)
    overall_percentage = Column(Numeric(5, 2))
    overall_gpa = Column(Numeric(3, 2))
    overall_grade = Column(String(5))
    
    # Ranking
    class_rank = Column(Integer)
    total_students = Column(Integer)
    
    # Subject-wise Grades (stored as JSON)
    subject_grades = Column(JSON)  # Detailed breakdown by subject
    
    # Additional Information
    attendance_percentage = Column(Numeric(5, 2))
    days_present = Column(Integer)
    days_absent = Column(Integer)
    
    # Comments
    class_teacher_comments = Column(Text)
    principal_comments = Column(Text)
    
    # Status
    is_published = Column(Boolean, default=False)
    published_date = Column(DateTime)
    
    # Generation Information
    generated_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    generated_date = Column(DateTime)
    report_url = Column(String(500))  # PDF report URL
    
    # Relationships
    tenant = relationship("Tenant")
    student = relationship("Student")
    class_ref = relationship("ClassModel")
    generated_by_authority = relationship("SchoolAuthority")

class GradeAuditLog(BaseModel):
    __tablename__ = "grade_audit_logs"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Reference Information
    reference_table = Column(String(50), nullable=False)  # "student_grades", "assessment_submissions"
    reference_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Change Information
    action = Column(String(20), nullable=False)  # "create", "update", "delete"
    old_values = Column(JSON)
    new_values = Column(JSON)
    changed_fields = Column(JSON)  # List of changed field names
    
    # Context
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"))
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"))
    
    # User Information
    changed_by = Column(UUID(as_uuid=True), ForeignKey("teachers.id"))
    change_reason = Column(String(200))
    
    # Relationships
    tenant = relationship("Tenant")
    student = relationship("Student")
    subject = relationship("Subject")
    assessment = relationship("Assessment")
    changed_by_teacher = relationship("Teacher")
