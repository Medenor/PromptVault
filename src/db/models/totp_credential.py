# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TotpCredential model for TOTP-based two-factor authentication.

One row per user. Holds the encrypted TOTP secret and confirmation state.
Created (or replaced) when enrollment starts; confirmed when the user
verifies a code.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class TotpCredential(Base):
    """TOTP credential model: one encrypted secret per user.

    Attributes:
        id: UUID primary key
        user_id: Foreign key to users table (unique — one credential per user)
        secret_ciphertext: AES-256-GCM ciphertext of the base32 TOTP secret (base64)
        secret_nonce: GCM nonce, hex-encoded, unique per encryption
        confirmed: False until the user verifies a code
        last_used_step: Last successfully-verified TOTP time-step (replay guard)
        created_at: Row creation timestamp
        confirmed_at: Timestamp the credential was confirmed, if any
        user: Relationship to User model
    """

    __tablename__ = "totp_credentials"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    secret_ciphertext: Mapped[str] = mapped_column(String, nullable=False)
    secret_nonce: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmed: Mapped[bool | None] = mapped_column(default=False)
    last_used_step: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="totp_credential")

    def __repr__(self):
        return f"<TotpCredential(id={self.id}, user_id={self.user_id}, confirmed={self.confirmed})>"
