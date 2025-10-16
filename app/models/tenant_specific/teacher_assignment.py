from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import BaseModel

class TeacherAssignment(BaseModel):
    __tablename__ = "teacher_assignments"
    
    # Foreign Keys
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"), nullable=False)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False)
    
    # Assignment Details
    subject = Column(String(100), nullable=False)
    academic_year = Column(String(10), nullable=False)
    
    # Relationships
    teacher = relationship("Teacher", back_populates="teaching_assignments")
    class_ref = relationship("ClassModel", back_populates="teaching_assignments")
