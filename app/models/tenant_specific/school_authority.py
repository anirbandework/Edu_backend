from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import Base


class SchoolAuthority(Base):
    __tablename__ = "school_authorities"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Basic Information
    authority_id = Column(String(20), nullable=False, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=False)
    date_of_birth = Column(DateTime, nullable=True)
    address = Column(String(500), nullable=True)
    gender = Column(String(10), nullable=True)
    
    # Role Information
    role = Column(String(20), default="school_authority", nullable=False)
    status = Column(String(20), default="active", nullable=False)
    position = Column(String(100), nullable=False)
    qualification = Column(String(500))
    experience_years = Column(Integer, default=0)
    joining_date = Column(DateTime, nullable=True)
    
    # Authority Details
    authority_details = Column(JSON)
    permissions = Column(JSON)
    school_overview = Column(JSON)
    contact_info = Column(JSON)
    last_login = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="authorities")
