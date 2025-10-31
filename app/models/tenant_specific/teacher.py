# app/models/tenant_specific/teacher.py
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import Base  # Updated import path

class Teacher(Base):
    __tablename__ = "teachers"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Basic Information
    teacher_id = Column(String(20), nullable=False, index=True)
    personal_info = Column(JSON)  # Contains all personal details
    contact_info = Column(JSON)   # Contains contact information
    family_info = Column(JSON)    # Contains family details
    
    # Professional Information
    qualifications = Column(JSON)         # Education and certifications
    employment = Column(JSON)            # Job details and salary
    academic_responsibilities = Column(JSON)  # Teaching assignments
    timetable = Column(JSON)             # Weekly schedule
    performance_evaluation = Column(JSON) # Performance data
    
    # Status
    status = Column(String(20), default="active", nullable=False)
    last_login = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="teachers")
    assignments = relationship("TeacherAssignment", back_populates="teacher")
    teacher_timetables = relationship("TeacherTimetable", back_populates="teacher_ref")
