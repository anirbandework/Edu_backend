from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from ..base import BaseModel
import enum

class FeeType(enum.Enum):
    TUITION = "tuition"
    REGISTRATION = "registration"
    LIBRARY = "library"
    LABORATORY = "laboratory"
    SPORTS = "sports"
    TRANSPORT = "transport"
    HOSTEL = "hostel"
    EXAMINATION = "examination"
    DEVELOPMENT = "development"
    MISCELLANEOUS = "miscellaneous"

class FeeFrequency(enum.Enum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMESTER = "semester"
    ANNUAL = "annual"
    WEEKLY = "weekly"

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    ONLINE = "online"
    UPI = "upi"
    WALLET = "wallet"

class FeeStructure(BaseModel):
    __tablename__ = "fee_structures"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=True, index=True)
    
    # Fee Information
    fee_name = Column(String(100), nullable=False)
    fee_type = Column(Enum(FeeType), nullable=False)
    fee_frequency = Column(Enum(FeeFrequency), nullable=False)
    
    # Amount Details
    base_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    
    # Applicability
    applicable_grades = Column(JSON)  # List of grade levels
    is_mandatory = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Time Period
    academic_year = Column(String(10), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_until = Column(Date)
    
    # Additional Details
    description = Column(Text)
    late_fee_amount = Column(Numeric(8, 2), default=0)
    late_fee_days = Column(Integer, default=30)  # Days after which late fee applies
    
    # Approval
    created_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    approval_date = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant")
    class_ref = relationship("ClassModel")
    created_by_authority = relationship("SchoolAuthority", foreign_keys=[created_by])
    approved_by_authority = relationship("SchoolAuthority", foreign_keys=[approved_by])
    student_fees = relationship("StudentFee", back_populates="fee_structure")

class StudentFee(BaseModel):
    __tablename__ = "student_fees"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    fee_structure_id = Column(UUID(as_uuid=True), ForeignKey("fee_structures.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=True, index=True)
    
    # Fee Details
    academic_year = Column(String(10), nullable=False)
    term = Column(String(20))  # "Term 1", "Semester 1", etc.
    
    # Amount Calculation
    base_amount = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0)
    scholarship_amount = Column(Numeric(10, 2), default=0)
    late_fee_amount = Column(Numeric(8, 2), default=0)
    adjustment_amount = Column(Numeric(8, 2), default=0)  # Manual adjustments
    final_amount = Column(Numeric(10, 2), nullable=False)
    
    # Payment Tracking
    paid_amount = Column(Numeric(10, 2), default=0)
    pending_amount = Column(Numeric(10, 2), nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Due Dates
    due_date = Column(Date, nullable=False)
    last_payment_date = Column(Date)
    
    # Additional Information
    discount_reason = Column(String(200))
    scholarship_details = Column(JSON)
    notes = Column(Text)
    
    # System Fields
    is_active = Column(Boolean, default=True)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    assigned_date = Column(DateTime, default=lambda: DateTime.utcnow())
    
    # Relationships
    tenant = relationship("Tenant")
    student = relationship("Student")
    fee_structure = relationship("FeeStructure", back_populates="student_fees")
    class_ref = relationship("ClassModel")
    assigned_by_authority = relationship("SchoolAuthority")
    payments = relationship("Payment", back_populates="student_fee")

class Payment(BaseModel):
    __tablename__ = "payments"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    student_fee_id = Column(UUID(as_uuid=True), ForeignKey("student_fees.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    
    # Payment Information
    payment_id = Column(String(50), unique=True, nullable=False, index=True)  # Receipt number
    payment_date = Column(DateTime, nullable=False)
    payment_amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    
    # Transaction Details
    transaction_id = Column(String(100))  # External transaction ID
    reference_number = Column(String(100))
    bank_name = Column(String(100))
    cheque_number = Column(String(50))
    cheque_date = Column(Date)
    
    # Status and Processing
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PAID)
    is_verified = Column(Boolean, default=False)
    verification_date = Column(DateTime)
    
    # Currency and Exchange
    currency = Column(String(3), default="USD")
    exchange_rate = Column(Numeric(10, 4), default=1.0000)
    
    # Receipt and Documentation
    receipt_number = Column(String(50), unique=True)
    receipt_generated = Column(Boolean, default=False)
    receipt_url = Column(String(500))
    
    # Additional Information
    payment_notes = Column(Text)
    late_fee_included = Column(Numeric(8, 2), default=0)
    
    # Processing Information
    collected_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    verified_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    
    # Refund Information
    is_refunded = Column(Boolean, default=False)
    refund_amount = Column(Numeric(10, 2), default=0)
    refund_date = Column(DateTime)
    refund_reason = Column(String(200))
    
    # Relationships
    tenant = relationship("Tenant")
    student_fee = relationship("StudentFee", back_populates="payments")
    student = relationship("Student")
    collected_by_authority = relationship("SchoolAuthority", foreign_keys=[collected_by])
    verified_by_authority = relationship("SchoolAuthority", foreign_keys=[verified_by])

class Scholarship(BaseModel):
    __tablename__ = "scholarships"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Scholarship Information
    scholarship_name = Column(String(100), nullable=False)
    scholarship_code = Column(String(20), unique=True, nullable=False)
    description = Column(Text)
    
    # Eligibility Criteria
    eligibility_criteria = Column(JSON)
    minimum_percentage = Column(Numeric(5, 2))
    applicable_grades = Column(JSON)
    family_income_limit = Column(Numeric(12, 2))
    
    # Award Details
    award_type = Column(String(20), default="percentage")  # "percentage", "fixed", "full"
    award_percentage = Column(Numeric(5, 2))  # If percentage type
    award_amount = Column(Numeric(10, 2))     # If fixed amount
    maximum_amount = Column(Numeric(10, 2))
    
    # Validity
    academic_year = Column(String(10), nullable=False)
    application_start_date = Column(Date)
    application_end_date = Column(Date)
    valid_from = Column(Date, nullable=False)
    valid_until = Column(Date)
    
    # Limits
    total_slots = Column(Integer)
    available_slots = Column(Integer)
    is_active = Column(Boolean, default=True)
    
    # Management
    created_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    
    # Relationships
    tenant = relationship("Tenant")
    created_by_authority = relationship("SchoolAuthority", foreign_keys=[created_by])
    approved_by_authority = relationship("SchoolAuthority", foreign_keys=[approved_by])
    applications = relationship("ScholarshipApplication", back_populates="scholarship")

class ScholarshipApplication(BaseModel):
    __tablename__ = "scholarship_applications"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    scholarship_id = Column(UUID(as_uuid=True), ForeignKey("scholarships.id"), nullable=False, index=True)
    
    # Application Information
    application_number = Column(String(50), unique=True, nullable=False)
    application_date = Column(DateTime, nullable=False)
    academic_year = Column(String(10), nullable=False)
    
    # Student Academic Information
    current_percentage = Column(Numeric(5, 2))
    previous_year_percentage = Column(Numeric(5, 2))
    family_income = Column(Numeric(12, 2))
    
    # Documents and Information
    supporting_documents = Column(JSON)
    application_essay = Column(Text)
    additional_information = Column(JSON)
    
    # Status and Processing
    status = Column(String(20), default="submitted")  # submitted, under_review, approved, rejected
    review_notes = Column(Text)
    approval_percentage = Column(Numeric(5, 2))  # Approved scholarship percentage
    approval_amount = Column(Numeric(10, 2))     # Approved scholarship amount
    
    # Processing Information
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    review_date = Column(DateTime)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    approval_date = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant")
    student = relationship("Student")
    scholarship = relationship("Scholarship", back_populates="applications")
    reviewed_by_authority = relationship("SchoolAuthority", foreign_keys=[reviewed_by])
    approved_by_authority = relationship("SchoolAuthority", foreign_keys=[approved_by])

class FeeTransaction(BaseModel):
    __tablename__ = "fee_transactions"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    
    # Transaction Information
    transaction_number = Column(String(50), unique=True, nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    transaction_type = Column(String(20), nullable=False)  # "payment", "refund", "adjustment", "late_fee"
    
    # Amount Information
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    
    # Reference Information
    reference_type = Column(String(20))  # "student_fee", "payment", "scholarship"
    reference_id = Column(UUID(as_uuid=True))
    
    # Description and Notes
    description = Column(String(200), nullable=False)
    notes = Column(Text)
    
    # Processing Information
    processed_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    
    # Relationships
    tenant = relationship("Tenant")
    student = relationship("Student")
    processed_by_authority = relationship("SchoolAuthority", foreign_keys=[processed_by])
    approved_by_authority = relationship("SchoolAuthority", foreign_keys=[approved_by])
