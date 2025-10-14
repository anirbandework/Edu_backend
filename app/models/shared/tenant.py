# app/models/shared/tenant.py
"""Tenant (School) model definition."""
from sqlalchemy import Column, String, Integer, Numeric, ARRAY, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from ..base import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    # Basic Information
    school_code = Column(String(10), unique=True, nullable=False, index=True)
    school_name = Column(String(200), nullable=False, index=True)
    address = Column(String(500), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=False)
    principal_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Financial Information
    annual_tuition = Column(Numeric(10, 2), nullable=False)
    registration_fee = Column(Numeric(8, 2), nullable=False)
    
    # Statistics
    total_students = Column(Integer, default=0)
    total_teachers = Column(Integer, default=0)
    total_staff = Column(Integer, default=0)
    maximum_capacity = Column(Integer, nullable=False)
    current_enrollment = Column(Integer, default=0)
    
    # Academic Information
    school_type = Column(String(20), default="K-12")
    grade_levels = Column(ARRAY(String), nullable=False)
    academic_year_start = Column(DateTime)
    academic_year_end = Column(DateTime)
    established_year = Column(Integer)
    accreditation = Column(String(50))
    language_of_instruction = Column(String(20), default="English")
    
    # Relationships
    authorities = relationship("SchoolAuthority", back_populates="tenant", cascade="all, delete-orphan")
    teachers = relationship("Teacher", back_populates="tenant", cascade="all, delete-orphan")
    students = relationship("Student", back_populates="tenant", cascade="all, delete-orphan")
    # classes = relationship("ClassModel", back_populates="tenant", cascade="all, delete-orphan")
    
    # Table-level unique constraints to prevent duplicate schools
    __table_args__ = (
        # Prevent duplicate email addresses
        UniqueConstraint('email', name='uq_tenant_email'),
        
        # Prevent duplicate phone numbers
        UniqueConstraint('phone', name='uq_tenant_phone'),
        
        # Prevent schools with same name at same address
        UniqueConstraint('school_name', 'address', name='uq_tenant_school_name_address'),
        
        # Optional: Prevent duplicate principal names at same school
        # UniqueConstraint('principal_name', 'school_name', name='uq_tenant_principal_school'),
    )

 