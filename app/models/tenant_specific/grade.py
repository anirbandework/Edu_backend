from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import BaseModel

class Grade(BaseModel):
    __tablename__ = "grades"
    
    # Foreign Keys
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    
    # Grade Details
    subject = Column(String(100), nullable=False)
    grade_value = Column(Numeric(5, 2), nullable=False)
    max_grade = Column(Numeric(5, 2), nullable=False)
    grade_type = Column(String(50), nullable=False)  # exam, assignment, quiz, etc.
    academic_year = Column(String(10), nullable=False)
    term = Column(String(20), nullable=False)
    
    # Relationships
    student = relationship("Student", back_populates="grades")
