# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TotpLoginChallenge model: short-lived, single-use login-challenge record.

Backs the login-challenge token issued after password validation succeeds
for a totp_enabled user. Created on password success, consumed (single
write) on successful TOTP/recovery-code exchange.
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


class TotpLoginChallenge(Base):
    """TOTP login challenge model.

    Attributes:
        id: UUID primary key — matches the `jti` claim of the challenge JWT
        user_id: Foreign key to users table
        expires_at: created_at + 2min
        consumed_at: Set on successful exchange; consumed/expired rows refuse reuse
        created_at: Row creation timestamp
        user: Relationship to User model
    """

    __tablename__ = "totp_login_challenges"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="totp_login_challenges")

    __table_args__ = (
        Index("ix_totp_login_challenges_user_consumed", "user_id", "consumed_at"),
    )

    def __repr__(self):
        return f"<TotpLoginChallenge(id={self.id}, user_id={self.user_id}, consumed_at={self.consumed_at})>"
