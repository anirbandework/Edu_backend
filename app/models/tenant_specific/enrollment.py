# app/models/tenant_specific/enrollment.py
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import Base  # Changed from BaseModel to Base

class Enrollment(Base):  # Changed from BaseModel to Base
    __tablename__ = "enrollments"
    
    # Foreign Keys
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False, index=True)
    
    # Enrollment Details
    enrollment_date = Column(DateTime, nullable=False)
    academic_year = Column(String(10), nullable=False)
    status = Column(String(20), default="active", nullable=False)
    
    # Relationships
    student = relationship("Student", back_populates="enrollments")
    class_ref = relationship("ClassModel", back_populates="enrollments")
