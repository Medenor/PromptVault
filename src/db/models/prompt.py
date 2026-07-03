# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt model for PromptVault.

This is the core model representing a prompt with its current state.
Version history is stored separately in PromptVersion model.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.base import Base


class Prompt(Base):
    """Main prompt model with current state.

    This model stores the current version of each prompt. Historical versions
    are stored in the PromptVersion model. Integer IDs are preserved from the
    JSON migration to maintain backward compatibility.

    Attributes:
        id: Integer primary key (preserved from JSON data, not auto-increment)
        title: Prompt title (1-200 chars, as per SPEC_APP.md REQ-006)
        prompt: Prompt content (1-50000 chars, as per SPEC_APP.md REQ-006)
        category_id: Foreign key to categories table
        note: Optional note/description (max 2000 chars, as per SPEC_APP.md REQ-006)
        favorite: Boolean flag for favorited prompts
        user_id: Foreign key to users table
        created_at: Timestamp when prompt was created
        updated_at: Timestamp when prompt was last updated
        category: Relationship to Category model
        tags: Many-to-many relationship to Tag model
        versions: One-to-many relationship to PromptVersion model
        branches: One-to-many relationship to PromptBranch model
        user: Relationship to User model
    """

    __tablename__ = "prompts"

    # Integer IDs with autoincrement (migration can override with explicit IDs)
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    prompt = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    note = Column(Text)
    favorite = Column(Boolean, default=False, index=True)
    semantic_version = Column(String(20), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    category = relationship("Category", back_populates="prompts")
    tags = relationship("Tag", secondary="prompt_tags", back_populates="prompts")
    versions = relationship(
        "PromptVersion",
        back_populates="parent_prompt",
        cascade="all, delete-orphan",
        order_by="PromptVersion.version_number",
    )
    branches = relationship(
        "PromptBranch", back_populates="prompt", cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="prompts")

    # Composite indices for common query patterns
    __table_args__ = (
        Index("idx_prompts_title", "title"),
        Index("idx_prompts_category", "category_id"),
        Index("idx_prompts_user", "user_id"),
    )

    def __repr__(self):
        return f"<Prompt(id={self.id}, title='{self.title[:30]}...')>"
