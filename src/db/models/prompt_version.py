# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""PromptVersion model for PromptVault.

This model implements Git-like version control for prompts. Each version
is an immutable snapshot with complete prompt data at that point in time.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.prompt import Prompt


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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(nullable=False)

    # Denormalized snapshot data
    title: Mapped[str | None] = mapped_column(String(200))
    prompt: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    note: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[Any | None] = mapped_column(
        JSON
    )  # Stored as JSON array for historical accuracy
    favorite: Mapped[bool | None] = mapped_column()

    semantic_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Version metadata
    author: Mapped[str | None] = mapped_column(String(100))
    message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Version graph (Git-like parent-child relationship)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("prompt_versions.version_id")
    )

    # Relationships
    parent_prompt: Mapped["Prompt"] = relationship("Prompt", back_populates="versions")
    parent_version: Mapped["PromptVersion | None"] = relationship(
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
