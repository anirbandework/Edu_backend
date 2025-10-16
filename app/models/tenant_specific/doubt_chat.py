from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from ..base import BaseModel
import enum

class ChatStatus(enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    RESOLVED = "resolved"
    PAUSED = "paused"

class MessageType(enum.Enum):
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    CODE = "code"
    MATH_FORMULA = "math_formula"

class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class ParticipantRole(enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"

class ChatRoom(BaseModel):
    __tablename__ = "chat_rooms"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=True, index=True)
    
    # Chat Information
    room_name = Column(String(200))  # Auto-generated or custom
    room_code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Chat Context
    topic = Column(String(300))  # Main doubt/topic
    description = Column(Text)   # Detailed description of the doubt
    urgency_level = Column(String(20), default="normal")  # "low", "normal", "high", "urgent"
    
    # Academic Context
    academic_year = Column(String(10), nullable=False)
    term = Column(String(20))
    chapter = Column(String(100))  # Related chapter/topic
    lesson = Column(String(200))   # Specific lesson
    
    # Chat Status and Timing
    status = Column(Enum(ChatStatus), default=ChatStatus.ACTIVE)
    started_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime)
    
    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolution_summary = Column(Text)
    student_feedback = Column(Text)
    teacher_feedback = Column(Text)
    
    # Metrics
    total_messages = Column(Integer, default=0)
    duration_minutes = Column(Integer, default=0)  # Total active duration
    
    # Settings
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant")
    student = relationship("Student", back_populates="chat_rooms")
    teacher = relationship("Teacher", back_populates="chat_rooms")
    subject = relationship("Subject")
    class_ref = relationship("ClassModel")
    messages = relationship("ChatMessage", back_populates="chat_room", cascade="all, delete-orphan")
    participants = relationship("ChatParticipant", back_populates="chat_room", cascade="all, delete-orphan")

class ChatParticipant(BaseModel):
    __tablename__ = "chat_participants"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False, index=True)
    participant_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Student or Teacher ID
    
    # Participant Information
    participant_role = Column(Enum(ParticipantRole), nullable=False)
    participant_name = Column(String(100), nullable=False)  # Cached for performance
    
    # Participation Details
    joined_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime)
    last_message_read_at = Column(DateTime)
    
    # Activity Metrics
    messages_sent = Column(Integer, default=0)
    total_time_spent = Column(Integer, default=0)  # In minutes
    
    # Status
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    
    # Notifications
    notifications_enabled = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant")
    chat_room = relationship("ChatRoom", back_populates="participants")

class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Student or Teacher ID
    
    # Message Information
    message_type = Column(Enum(MessageType), default=MessageType.TEXT, nullable=False)
    content = Column(Text, nullable=False)
    
    # Sender Details (cached for performance)
    sender_role = Column(Enum(ParticipantRole), nullable=False)
    sender_name = Column(String(100), nullable=False)
    
    # Message Metadata
    message_sequence = Column(Integer, nullable=False)  # Sequential number in chat
    sent_at = Column(DateTime, nullable=False, index=True)
    
    # Reply/Thread Information
    reply_to_message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id"))
    is_reply = Column(Boolean, default=False)
    
    # File/Media Information (for non-text messages)
    file_metadata = Column(JSON)  # File details like size, name, type, URL
    attachments = Column(JSON)    # Multiple attachments
    
    # Message Status and Delivery
    status = Column(Enum(MessageStatus), default=MessageStatus.SENT)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)
    
    # Message Actions
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime)
    original_content = Column(Text)  # Store original before edit
    
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)
    deleted_by = Column(UUID(as_uuid=True))  # Who deleted it
    
    # Special Message Types
    is_system_message = Column(Boolean, default=False)  # System generated messages
    is_important = Column(Boolean, default=False)       # Marked as important
    is_pinned = Column(Boolean, default=False)          # Pinned message
    
    # Academic Context
    related_topic = Column(String(200))  # Specific topic/concept being discussed
    difficulty_level = Column(String(20))  # "basic", "intermediate", "advanced"
    
    # Relationships
    tenant = relationship("Tenant")
    chat_room = relationship("ChatRoom", back_populates="messages")
    reply_to_message = relationship("ChatMessage", remote_side="ChatMessage.id")
    reactions = relationship("MessageReaction", back_populates="message", cascade="all, delete-orphan")

class MessageReaction(BaseModel):
    __tablename__ = "message_reactions"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Who reacted
    
    # Reaction Information
    reaction_type = Column(String(50), nullable=False)  # "like", "helpful", "understood", "confused", etc.
    reaction_emoji = Column(String(10))  # Emoji representation
    
    # Timing
    reacted_at = Column(DateTime, nullable=False)
    
    # User Info (cached)
    user_role = Column(Enum(ParticipantRole), nullable=False)
    user_name = Column(String(100), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
    message = relationship("ChatMessage", back_populates="reactions")

class ChatSession(BaseModel):
    __tablename__ = "chat_sessions"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False, index=True)
    participant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Session Information
    session_token = Column(String(255), unique=True, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime)
    last_activity_at = Column(DateTime, nullable=False)
    
    # Connection Details
    connection_id = Column(String(255))  # WebSocket connection ID
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    device_info = Column(JSON)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant")
    chat_room = relationship("ChatRoom")

class DoubtCategory(BaseModel):
    __tablename__ = "doubt_categories"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True)
    
    # Category Information
    category_name = Column(String(100), nullable=False)
    category_code = Column(String(50), nullable=False)
    description = Column(Text)
    
    # Hierarchy (keep the column for future use)
    parent_category_id = Column(UUID(as_uuid=True), ForeignKey("doubt_categories.id"))
    level = Column(Integer, default=1)
    
    # Academic Context
    academic_year = Column(String(10), nullable=False)
    applicable_grades = Column(JSON)
    
    # Usage Statistics
    usage_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Basic Relationships only
    tenant = relationship("Tenant")
    subject = relationship("Subject")
    
    # Note: Self-referential relationships removed for simplicity
    # You can query parent/children using parent_category_id directly




class ChatAnalytics(BaseModel):
    __tablename__ = "chat_analytics"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False, index=True)
    
    # Time Period
    date = Column(DateTime, nullable=False, index=True)
    
    # Activity Metrics
    total_messages = Column(Integer, default=0)
    student_messages = Column(Integer, default=0)
    teacher_messages = Column(Integer, default=0)
    
    # Engagement Metrics
    active_duration_minutes = Column(Integer, default=0)
    response_time_avg_seconds = Column(Integer, default=0)  # Average teacher response time
    
    # Resolution Metrics
    doubt_resolved = Column(Boolean, default=False)
    resolution_time_minutes = Column(Integer, default=0)
    student_satisfaction_rating = Column(Integer)  # 1-5 rating
    
    # Content Analysis
    topics_discussed = Column(JSON)  # List of topics covered
    difficulty_level = Column(String(20))
    
    # Relationships
    tenant = relationship("Tenant")
    chat_room = relationship("ChatRoom")

class TeacherAvailability(BaseModel):
    __tablename__ = "teacher_availability"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True)
    
    # Availability Information
    day_of_week = Column(String(10), nullable=False)  # "monday", "tuesday", etc.
    start_time = Column(String(8), nullable=False)    # "09:00:00" format
    end_time = Column(String(8), nullable=False)      # "17:00:00" format
    
    # Availability Settings
    max_concurrent_chats = Column(Integer, default=3)
    current_active_chats = Column(Integer, default=0)
    
    # Status
    is_available = Column(Boolean, default=True)
    auto_accept_chats = Column(Boolean, default=False)
    
    # Academic Context
    academic_year = Column(String(10), nullable=False)
    applicable_grades = Column(JSON)  # Which grades teacher supports
    
    # Preferences
    preferred_topics = Column(JSON)    # Topics teacher specializes in
    response_time_commitment = Column(String(50))  # "immediate", "within_hour", etc.
    
    # Relationships
    tenant = relationship("Tenant")
    teacher = relationship("Teacher")
    subject = relationship("Subject")
