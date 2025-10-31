from sqlalchemy.orm import as_declarative, declared_attr
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, Boolean, func, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid


@as_declarative()
class Base:
    __abstract__ = True  # Prevents creating a table for the base class
    
    id: Mapped[uuid.UUID]
    
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # Use proper PostgreSQL UUID type with auto-generation
    id = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Soft delete functionality for EduAssist - indexed for performance
    is_deleted = mapped_column(Boolean, default=False, nullable=False, index=True)
