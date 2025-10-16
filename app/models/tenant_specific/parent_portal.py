from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from ..base import BaseModel
import enum

class ParentRelationship(enum.Enum):
    FATHER = "father"
    MOTHER = "mother"
    GUARDIAN = "guardian"
    STEP_FATHER = "step_father"
    STEP_MOTHER = "step_mother"
    GRANDPARENT = "grandparent"
    OTHER = "other"

class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    ARCHIVED = "archived"

class MessageType(enum.Enum):
    ANNOUNCEMENT = "announcement"
    PERSONAL = "personal"
    URGENT = "urgent"
    HOMEWORK = "homework"
    EVENT = "event"
    DISCIPLINARY = "disciplinary"

class NotificationType(enum.Enum):
    ATTENDANCE = "attendance"
    GRADES = "grades"
    FEES = "fees"
    EVENTS = "events"
    HOMEWORK = "homework"
    DISCIPLINARY = "disciplinary"
    GENERAL = "general"

class Parent(BaseModel):
    __tablename__ = "parents"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Basic Information
    parent_id = Column(String(20), nullable=False, unique=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    middle_name = Column(String(50))
    
    # Contact Information
    email = Column(String(100), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=False)
    alternate_phone = Column(String(20))
    whatsapp_number = Column(String(20))
    
    # Address Information
    address = Column(JSON)  # Detailed address structure
    
    # Professional Information
    occupation = Column(String(100))
    employer = Column(String(100))
    annual_income = Column(String(20))  # Income range
    
    # Portal Access
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    login_attempts = Column(Integer, default=0)
    account_locked = Column(Boolean, default=False)
    locked_until = Column(DateTime)
    
    # Preferences
    communication_preferences = Column(JSON)  # Email, SMS, app notifications
    notification_settings = Column(JSON)  # What notifications to receive
    language_preference = Column(String(10), default="en")
    
    # Security
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    reset_token = Column(String(255))
    reset_token_expires = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant")
    student_parents = relationship("StudentParent", back_populates="parent")
    messages = relationship("ParentMessage", back_populates="parent")
    notifications = relationship("ParentNotification", back_populates="parent")

class StudentParent(BaseModel):
    __tablename__ = "student_parents"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("parents.id"), nullable=False, index=True)
    
    # Relationship Information
    relationship = Column(Enum(ParentRelationship), nullable=False)
    is_primary_contact = Column(Boolean, default=False)
    is_emergency_contact = Column(Boolean, default=False)
    is_authorized_pickup = Column(Boolean, default=True)
    
    # Permissions
    can_view_grades = Column(Boolean, default=True)
    can_view_attendance = Column(Boolean, default=True)
    can_view_disciplinary = Column(Boolean, default=True)
    can_receive_communications = Column(Boolean, default=True)
    can_make_payments = Column(Boolean, default=False)
    
    # Additional Information
    notes = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant")
    student = relationship("Student")
    parent = relationship("Parent", back_populates="student_parents")

class ParentMessage(BaseModel):
    __tablename__ = "parent_messages"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("parents.id"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True))  # Can be teacher, authority, or system
    sender_type = Column(String(20))  # "teacher", "authority", "system"
    
    # Message Information
    message_type = Column(Enum(MessageType), nullable=False)
    subject = Column(String(200), nullable=False)
    message_body = Column(Text, nullable=False)
    
    # Student Context (if applicable)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    
    # Attachments and Media
    attachments = Column(JSON)  # File URLs and metadata
    
    # Status and Tracking
    status = Column(Enum(MessageStatus), default=MessageStatus.SENT)
    sent_date = Column(DateTime, nullable=False)
    read_date = Column(DateTime)
    archived_date = Column(DateTime)
    
    # Priority
    is_urgent = Column(Boolean, default=False)
    requires_response = Column(Boolean, default=False)
    response_deadline = Column(DateTime)
    
    # Threading
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("parent_messages.id"))
    thread_subject = Column(String(200))
    
    # Relationships
    tenant = relationship("Tenant")
    parent = relationship("Parent", back_populates="messages")
    student = relationship("Student")
    replies = relationship("ParentMessage", backref="parent_message", remote_side="ParentMessage.id")

class ParentNotification(BaseModel):
    __tablename__ = "parent_notifications"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("parents.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    
    # Notification Information
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    
    # Reference Information
    reference_type = Column(String(50))  # "attendance", "grade", "fee", etc.
    reference_id = Column(UUID(as_uuid=True))
    
    # Delivery Information
    sent_date = Column(DateTime, nullable=False)
    delivery_channels = Column(JSON)  # ["email", "sms", "app"]
    delivery_status = Column(JSON)  # Status per channel
    
    # Status
    is_read = Column(Boolean, default=False)
    read_date = Column(DateTime)
    is_archived = Column(Boolean, default=False)
    
    # Priority
    priority = Column(String(10), default="normal")  # "low", "normal", "high", "urgent"
    
    # Auto-generated or Manual
    is_auto_generated = Column(Boolean, default=True)
    generated_by = Column(UUID(as_uuid=True))  # User who triggered manual notification
    
    # Relationships
    tenant = relationship("Tenant")
    parent = relationship("Parent", back_populates="notifications")
    student = relationship("Student")

class ParentPortalSession(BaseModel):
    __tablename__ = "parent_portal_sessions"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("parents.id"), nullable=False, index=True)
    
    # Session Information
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    login_time = Column(DateTime, nullable=False)
    logout_time = Column(DateTime)
    expires_at = Column(DateTime, nullable=False)
    
    # Access Information
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    device_info = Column(JSON)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant")
    parent = relationship("Parent")

class ParentFeedback(BaseModel):
    __tablename__ = "parent_feedback"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("parents.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    
    # Feedback Information
    feedback_type = Column(String(50), nullable=False)  # "general", "teacher", "facility", "curriculum"
    subject = Column(String(200), nullable=False)
    feedback_text = Column(Text, nullable=False)
    rating = Column(Integer)  # 1-5 star rating
    
    # Context
    related_teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"))
    related_subject = Column(String(100))
    academic_year = Column(String(10))
    
    # Status
    status = Column(String(20), default="submitted")  # "submitted", "under_review", "responded", "closed"
    response = Column(Text)
    responded_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    response_date = Column(DateTime)
    
    # Anonymous Option
    is_anonymous = Column(Boolean, default=False)
    
    # Relationships
    tenant = relationship("Tenant")
    parent = relationship("Parent")
    student = relationship("Student")
    related_teacher = relationship("Teacher")
    responded_by_authority = relationship("SchoolAuthority")

class ParentEvent(BaseModel):
    __tablename__ = "parent_events"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Event Information
    event_title = Column(String(200), nullable=False)
    event_description = Column(Text)
    event_type = Column(String(50))  # "meeting", "workshop", "sports_day", "annual_day"
    
    # Scheduling
    event_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    duration_minutes = Column(Integer)
    location = Column(String(200))
    
    # Target Audience
    target_grades = Column(JSON)  # Which grade levels
    target_classes = Column(JSON)  # Specific classes
    is_mandatory = Column(Boolean, default=False)
    
    # Registration
    requires_registration = Column(Boolean, default=False)
    registration_deadline = Column(DateTime)
    max_participants = Column(Integer)
    current_participants = Column(Integer, default=0)
    
    # Content
    agenda = Column(JSON)  # Event agenda/schedule
    attachments = Column(JSON)  # Documents, forms
    
    # Status
    is_active = Column(Boolean, default=True)
    is_cancelled = Column(Boolean, default=False)
    cancellation_reason = Column(Text)
    
    # Organization
    organized_by = Column(UUID(as_uuid=True), ForeignKey("school_authorities.id"))
    
    # Relationships
    tenant = relationship("Tenant")
    organized_by_authority = relationship("SchoolAuthority")
    registrations = relationship("ParentEventRegistration", back_populates="event")

class ParentEventRegistration(BaseModel):
    __tablename__ = "parent_event_registrations"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("parent_events.id"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("parents.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    
    # Registration Information
    registration_date = Column(DateTime, nullable=False)
    number_of_attendees = Column(Integer, default=1)
    attendee_names = Column(JSON)  # List of attendee names
    
    # Status
    status = Column(String(20), default="registered")  # "registered", "confirmed", "cancelled"
    confirmation_date = Column(DateTime)
    
    # Additional Information
    special_requirements = Column(Text)
    contact_phone = Column(String(20))
    
    # Relationships
    tenant = relationship("Tenant")
    event = relationship("ParentEvent", back_populates="registrations")
    parent = relationship("Parent")
    student = relationship("Student")
