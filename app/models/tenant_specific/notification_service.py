from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from ..base import BaseModel
import enum

class NotificationType(enum.Enum):
    ANNOUNCEMENT = "announcement"
    URGENT = "urgent"
    ASSIGNMENT = "assignment"
    GRADE = "grade"
    ATTENDANCE = "attendance"
    EVENT = "event"
    REMINDER = "reminder"
    DISCIPLINARY = "disciplinary"
    SYSTEM = "system"
    PERSONAL = "personal"

class NotificationPriority(enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationStatus(enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    ARCHIVED = "archived"
    FAILED = "failed"

class DeliveryChannel(enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WHATSAPP = "whatsapp"

class RecipientType(enum.Enum):
    INDIVIDUAL = "individual"
    CLASS = "class"
    GRADE = "grade"
    ALL_STUDENTS = "all_students"
    ALL_TEACHERS = "all_teachers"
    DEPARTMENT = "department"
    CUSTOM_GROUP = "custom_group"

class SenderType(enum.Enum):
    SCHOOL_AUTHORITY = "school_authority"
    TEACHER = "teacher"
    SYSTEM = "system"

class Notification(BaseModel):
    __tablename__ = "notifications"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Can be authority or teacher
    sender_type = Column(Enum(SenderType), nullable=False)
    
    # Notification Content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    
    # Recipient Configuration
    recipient_type = Column(Enum(RecipientType), nullable=False)
    recipient_config = Column(JSON)  # Configuration for recipients
    
    # Delivery Configuration  
    delivery_channels = Column(JSON)  # List of channels to use
    scheduled_at = Column(DateTime)  # For scheduled notifications
    expires_at = Column(DateTime)    # When notification expires
    
    # Content and Media
    attachments = Column(JSON)  # File attachments
    action_url = Column(String(500))  # URL for call-to-action
    action_text = Column(String(100))  # Text for action button
    
    # Delivery Tracking
    total_recipients = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    read_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Status and Timing
    status = Column(Enum(NotificationStatus), default=NotificationStatus.DRAFT)
    sent_at = Column(DateTime)
    
    # Additional Information
    category = Column(String(50))  # Custom categorization
    tags = Column(JSON)  # Tags for organization
    
    # Academic Context
    academic_year = Column(String(10))
    term = Column(String(20))
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"))
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"))
    
    # Auto-deletion
    auto_delete_at = Column(DateTime)  # Auto-delete after certain period
    
    # Relationships
    tenant = relationship("Tenant")
    subject = relationship("Subject")
    class_ref = relationship("ClassModel")
    recipients = relationship("NotificationRecipient", back_populates="notification", cascade="all, delete-orphan")
    delivery_logs = relationship("NotificationDeliveryLog", back_populates="notification", cascade="all, delete-orphan")

class NotificationRecipient(BaseModel):
    __tablename__ = "notification_recipients"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    notification_id = Column(UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False, index=True)
    recipient_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Student or teacher ID
    recipient_type = Column(String(20), nullable=False)  # "student" or "teacher"
    
    # Delivery Status
    status = Column(Enum(NotificationStatus), default=NotificationStatus.SENT)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)
    clicked_at = Column(DateTime)
    
    # Channel-specific delivery status
    delivery_status = Column(JSON)  # Status per channel
    
    # User Actions
    is_starred = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    
    # Response/Interaction
    has_responded = Column(Boolean, default=False)
    response_data = Column(JSON)
    
    # Relationships
    tenant = relationship("Tenant")
    notification = relationship("Notification", back_populates="recipients")

class NotificationTemplate(BaseModel):
    __tablename__ = "notification_templates"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_by_type = Column(Enum(SenderType), nullable=False)
    
    # Template Information
    template_name = Column(String(100), nullable=False)
    template_code = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    
    # Template Content
    subject_template = Column(String(200), nullable=False)
    body_template = Column(Text, nullable=False)
    
    # Template Configuration
    notification_type = Column(Enum(NotificationType), nullable=False)
    default_priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    supported_channels = Column(JSON)  # Supported delivery channels
    
    # Variables and Placeholders
    template_variables = Column(JSON)  # Available variables for template
    sample_data = Column(JSON)  # Sample data for preview
    
    # Usage and Status
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    
    # Categories
    category = Column(String(50))
    tags = Column(JSON)
    
    # Relationships
    tenant = relationship("Tenant")

class NotificationDeliveryLog(BaseModel):
    __tablename__ = "notification_delivery_logs"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    notification_id = Column(UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False, index=True)
    recipient_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Delivery Information
    channel = Column(Enum(DeliveryChannel), nullable=False)
    delivery_attempt = Column(Integer, default=1)
    
    # Status and Timing
    status = Column(String(20), nullable=False)  # "success", "failed", "pending"
    attempted_at = Column(DateTime, nullable=False)
    delivered_at = Column(DateTime)
    
    # Channel-specific Information
    channel_identifier = Column(String(200))  # Email address, phone number, etc.
    external_reference = Column(String(100))  # External service reference ID
    
    # Error Information
    error_code = Column(String(50))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Response Information
    response_data = Column(JSON)  # Response from delivery service
    
    # Relationships
    tenant = relationship("Tenant")
    notification = relationship("Notification", back_populates="delivery_logs")

class NotificationPreference(BaseModel):
    __tablename__ = "notification_preferences"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Student or teacher ID
    user_type = Column(String(20), nullable=False)  # "student" or "teacher"
    
    # Preference Configuration
    notification_type = Column(Enum(NotificationType), nullable=False)
    
    # Channel Preferences
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    push_enabled = Column(Boolean, default=True)
    in_app_enabled = Column(Boolean, default=True)
    
    # Timing Preferences
    quiet_hours_start = Column(String(5))  # "22:00" format
    quiet_hours_end = Column(String(5))    # "08:00" format
    timezone = Column(String(50), default="UTC")
    
    # Frequency Limits
    max_daily_notifications = Column(Integer, default=50)
    max_weekly_digest = Column(Boolean, default=True)
    
    # Priority Filtering
    min_priority = Column(Enum(NotificationPriority), default=NotificationPriority.LOW)
    
    # Relationships
    tenant = relationship("Tenant")

class NotificationGroup(BaseModel):
    __tablename__ = "notification_groups"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_by_type = Column(Enum(SenderType), nullable=False)
    
    # Group Information
    group_name = Column(String(100), nullable=False)
    group_code = Column(String(50), nullable=False)
    description = Column(Text)
    
    # Group Configuration
    group_type = Column(String(20), nullable=False)  # "static", "dynamic"
    members = Column(JSON)  # List of member IDs if static
    criteria = Column(JSON)  # Selection criteria if dynamic
    
    # Member counts
    total_members = Column(Integer, default=0)
    active_members = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant")

class NotificationSchedule(BaseModel):
    __tablename__ = "notification_schedules"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    notification_template_id = Column(UUID(as_uuid=True), ForeignKey("notification_templates.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    
    # Schedule Information
    schedule_name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Timing Configuration
    schedule_type = Column(String(20), nullable=False)  # "once", "daily", "weekly", "monthly"
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    
    # Recurrence Pattern
    recurrence_pattern = Column(JSON)  # Detailed recurrence configuration
    timezone = Column(String(50), default="UTC")
    
    # Recipients
    recipient_config = Column(JSON)  # Who receives scheduled notifications
    
    # Status
    is_active = Column(Boolean, default=True)
    next_run = Column(DateTime)
    last_run = Column(DateTime)
    run_count = Column(Integer, default=0)
    
    # Relationships
    tenant = relationship("Tenant")
    template = relationship("NotificationTemplate")
