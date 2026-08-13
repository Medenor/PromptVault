# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TotpRecoveryCode model for 2FA account-recovery codes.

Multiple rows per user per batch. A regeneration event creates a new batch
and invalidates the old one; only the latest batch per user is valid.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class TotpRecoveryCode(Base):
    """TOTP recovery code model: one Argon2id-hashed code per row.

    Attributes:
        id: UUID primary key
        user_id: Foreign key to users table
        batch_id: Groups codes issued together; only the latest batch is valid
        code_hash: Argon2id hash of the code (reuses PasswordService hasher)
        used_at: NULL = unused; set on consumption
        created_at: Row creation timestamp
        user: Relationship to User model
    """

    __tablename__ = "totp_recovery_codes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="totp_recovery_codes")

    __table_args__ = (
        Index("ix_totp_recovery_codes_user_batch", "user_id", "batch_id"),
    )

    def __repr__(self):
        return f"<TotpRecoveryCode(id={self.id}, user_id={self.user_id}, batch_id={self.batch_id}, used_at={self.used_at})>"
