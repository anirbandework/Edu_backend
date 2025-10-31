# app/models/tenant_specific/class_model.py
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import Base  # Changed from BaseModel to Base
from sqlalchemy import UniqueConstraint


class ClassModel(Base):  # Changed from BaseModel to Base
    __tablename__ = "classes"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Class Information
    class_name = Column(String(50), nullable=False, index=True)
    grade_level = Column(Integer, nullable=False)
    section = Column(String(10), nullable=False)
    academic_year = Column(String(10), nullable=False)
    maximum_students = Column(Integer, default=40)
    current_students = Column(Integer, default=0)
    classroom = Column(String(50))
    is_active = Column(Boolean, default=True)
    

    __table_args__ = (
        UniqueConstraint("tenant_id", "class_name", "section", "academic_year", name="uq_class_identity"),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="classes")
    enrollments = relationship("Enrollment", back_populates="class_ref")
    teacher_assignments = relationship("TeacherAssignment", back_populates="class_ref")
    class_timetables = relationship("ClassTimetable", back_populates="class_ref")
    attendances = relationship("Attendance", back_populates="class_ref")
