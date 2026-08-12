# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""PromptVersion model for PromptVault.

This model implements Git-like version control for prompts. Each version
is an immutable snapshot with complete prompt data at that point in time.
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.base import Base


class PromptVersion(Base):
    """Version history model for prompts (Git-like versioning).

    Each version stores a complete snapshot of the prompt data at a specific
    point in time. This follows the Git-like pattern specified in SPEC_APP.md
    (REQ-002, REQ-003, PAT-001).

    Denormalized storage: Each version contains the full prompt state for
    historical accuracy, even if it duplicates current prompt data.

    Attributes:
        id: Auto-incrementing integer primary key
        prompt_id: Foreign key to prompts table
        version_id: UUID unique identifier for this version
        version_number: Sequential version number (1, 2, 3...)
        title: Snapshot of title at this version
        prompt: Snapshot of prompt content at this version
        category_id: Snapshot of category at this version
        note: Snapshot of note at this version
        tags: JSON array of tags at this version (denormalized)
        favorite: Snapshot of favorite flag at this version
        author: Username who created this version
        message: Commit message describing changes (1-500 chars, REQ-006)
        created_at: Timestamp when version was created
        parent_version_id: Link to parent version (for version graph)
        prompt: Relationship to parent Prompt model
        parent_version: Self-referential relationship to parent version
        child_versions: Self-referential relationship to child versions
    """

    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    version_id = Column(String(36), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    # Denormalized snapshot data
    title = Column(String(200))
    prompt = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id"))
    note = Column(Text)
    tags = Column(JSON)  # Stored as JSON array for historical accuracy
    favorite = Column(Boolean)

    semantic_version = Column(String(20), nullable=True)

    # Version metadata
    author = Column(String(100))
    message = Column(String(500))
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Version graph (Git-like parent-child relationship)
    parent_version_id = Column(String(36), ForeignKey("prompt_versions.version_id"))

    # Relationships
    parent_prompt = relationship("Prompt", back_populates="versions")
    parent_version = relationship(
        "PromptVersion",
        remote_side=[version_id],
        foreign_keys=[parent_version_id],
        backref="child_versions",
    )

    # Constraints and indices
    __table_args__ = (
        UniqueConstraint(
            "prompt_id", "version_number", name="uq_prompt_version_number"
        ),
        UniqueConstraint("version_id", name="uq_version_id"),
        Index("idx_versions_prompt", "prompt_id"),
        Index("idx_versions_created", "created_at"),
        Index("idx_versions_parent", "parent_version_id"),
    )

    def __repr__(self):
        return f"<PromptVersion(id={self.id}, prompt_id={self.prompt_id}, version={self.version_number}, version_id='{self.version_id[:8]}...')>"
