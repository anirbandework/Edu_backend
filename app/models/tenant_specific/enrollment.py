from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import BaseModel

class Enrollment(BaseModel):
    __tablename__ = "enrollments"
    
    # Foreign Keys
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False)
    
    # Enrollment Details
    enrollment_date = Column(DateTime, nullable=False)
    academic_year = Column(String(10), nullable=False)
    status = Column(String(20), default="active", nullable=False)
    
    # Relationships
    student = relationship("Student", back_populates="enrollments")
    class_ref = relationship("ClassModel", back_populates="enrollments")
