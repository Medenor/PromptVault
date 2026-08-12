# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tag model for PromptVault.

Tags provide flexible categorization and labeling for prompts.
Multiple tags can be associated with each prompt via many-to-many relationship.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.base import Base


class Tag(Base):
    """Tag model for flexible prompt categorization.

    Attributes:
        id: Auto-incrementing integer primary key
        name: Unique tag name (max 50 chars, as per SPEC_APP.md REQ-006)
        created_at: Timestamp when tag was created
        updated_at: Timestamp when tag was last updated
        description: Optional tag description
        color: Optional display color token or hex value
        parent_tag_id: Optional parent tag for hierarchy
        parent: Parent tag relationship
        children: Child tag relationship
        prompts: Relationship to prompts with this tag (many-to-many)
    """

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    description = Column(Text)
    color = Column(String(20))
    parent_tag_id = Column(Integer, ForeignKey("tags.id", ondelete="SET NULL"))

    # Relationships - many-to-many with prompts via prompt_tags association table
    parent = relationship("Tag", remote_side=[id], back_populates="children")
    children = relationship("Tag", back_populates="parent")
    prompts = relationship("Prompt", secondary="prompt_tags", back_populates="tags")

    __table_args__ = (Index("ix_tags_name_lower", func.lower(name), unique=True),)

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"
