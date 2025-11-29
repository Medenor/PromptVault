"""User model for PromptVault.

This model represents user accounts in the system. Authentication and
authorization features are deferred to a future phase (separate ticket).
For now, a default 'system' user will be created during migration.
"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.db.base import Base


class User(Base):
    """User account model.

    Attributes:
        id: UUID primary key (PostgreSQL UUID, String(36) for SQLite)
        username: Unique username (max 100 chars)
        display_name: Optional display name (max 200 chars)
        email: Optional email address (max 255 chars)
        role: User role (default 'user', max 50 chars)
        created_at: Timestamp when user was created
        prompts: Relationship to user's prompts
    """
    __tablename__ = "users"

    # Use UUID for PostgreSQL, String for SQLite compatibility
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200))
    email = Column(String(255))
    role = Column(String(50), default='user')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    prompts = relationship("Prompt", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
