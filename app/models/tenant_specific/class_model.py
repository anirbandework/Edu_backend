# services/api-gateway/app/models/tenant_specific/class_model.py
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import BaseModel

class ClassModel(BaseModel):
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
    
    # Relationships
    tenant = relationship("Tenant", back_populates="classes")
    enrollments = relationship("Enrollment", back_populates="class_ref")
    teaching_assignments = relationship("TeacherAssignment", back_populates="class_ref")
