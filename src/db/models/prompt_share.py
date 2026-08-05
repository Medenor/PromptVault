# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""PromptShare model for per-prompt sharing grants.

One row per (prompt, grantee) pair — a grant of read or edit access to a
prompt, made by its owner (or an admin) to another user.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Enum,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.base import Base


class PromptShare(Base):
    """A grant of access to a prompt, from its owner to another user.

    Attributes:
        id: Surrogate primary key
        prompt_id: Prompt being shared (cascades on prompt delete)
        grantee_user_id: User receiving access (cascades on grantee delete)
        permission: 'read' or 'edit'
        granted_by: User who created the grant (SET NULL on grantor delete —
            the grant itself survives)
        created_at: Grant creation time
        updated_at: Bumped on permission-level change (upsert)
    """

    __tablename__ = "prompt_shares"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(
        Integer,
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
    )
    grantee_user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_prompt_shares_grantee_user_id_users"),
        nullable=False,
    )
    permission = Column(
        Enum(
            "read",
            "edit",
            name="share_permission",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )
    granted_by = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL", name="fk_prompt_shares_granted_by_users"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    prompt = relationship("Prompt", back_populates="shares")
    grantee = relationship(
        "User", foreign_keys=[grantee_user_id], back_populates="received_shares"
    )
    granted_by_user = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        UniqueConstraint(
            "prompt_id", "grantee_user_id", name="uq_prompt_shares_prompt_grantee"
        ),
        Index("idx_prompt_shares_grantee", "grantee_user_id"),
    )

    def __repr__(self):
        return (
            f"<PromptShare(prompt_id={self.prompt_id}, "
            f"grantee_user_id={self.grantee_user_id!r}, permission={self.permission!r})>"
        )
