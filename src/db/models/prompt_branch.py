# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""PromptBranch model for PromptVault.

This model implements Git-like branching for prompt version control.
Each prompt can have multiple branches pointing to different versions.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.db.base import Base


class PromptBranch(Base):
    """Branch pointer model for prompt version control (Git-like).

    Branches are named pointers to specific versions, similar to Git branches.
    The 'main' branch is the default branch for each prompt.

    Attributes:
        id: Auto-incrementing integer primary key
        prompt_id: Foreign key to prompts table
        branch_name: Name of the branch (default 'main')
        current_version_id: UUID of the version this branch points to
        prompt: Relationship to parent Prompt model
        current_version: Relationship to the version this branch points to
    """

    __tablename__ = "prompt_branches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    branch_name = Column(String(50), nullable=False, default="main")
    current_version_id = Column(String(36), ForeignKey("prompt_versions.version_id"))

    # Relationships
    prompt = relationship("Prompt", back_populates="branches")
    current_version = relationship("PromptVersion", foreign_keys=[current_version_id])

    # Unique constraint: one branch name per prompt
    __table_args__ = (
        UniqueConstraint("prompt_id", "branch_name", name="uq_prompt_branch_name"),
    )

    def __repr__(self):
        return f"<PromptBranch(prompt_id={self.prompt_id}, branch='{self.branch_name}', version='{self.current_version_id[:8]}...')>"
