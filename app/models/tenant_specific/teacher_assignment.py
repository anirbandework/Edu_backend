# app/models/tenant_specific/teacher_assignment.py
#Creating TeacherAssignment model to establish proper relationship between teachers and classes
from sqlalchemy import Column, String, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import Base

class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False, index=True)
    
    # Assignment Details
    subject_name = Column(String(100), nullable=False)
    academic_year = Column(String(10), nullable=False)
    is_primary_teacher = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('teacher_id', 'class_id', 'subject_name', 'academic_year', name='unique_teacher_class_subject'),
    )
    
    # Relationships
    tenant = relationship("Tenant")
    teacher = relationship("Teacher", back_populates="assignments")
    class_ref = relationship("ClassModel", back_populates="teacher_assignments")