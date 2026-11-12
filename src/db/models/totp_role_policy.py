# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TotpRolePolicy model: admin-configured per-role 2FA enforcement.

Rows are upserted by admin policy updates; absence of a row for a role is
equivalent to required=False. Checked at login for users without
totp_enabled.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class TotpRolePolicy(Base):
    """Per-role required-2FA policy.

    Attributes:
        role: Role name primary key (matches users.role values)
        required: Whether members of this role must have 2FA enabled
        updated_at: Timestamp of last policy change
        updated_by_user_id: Admin who last changed the policy (audit trail)
        updated_by: Relationship to the admin User who last changed the policy
    """

    __tablename__ = "totp_role_policies"

    role: Mapped[str] = mapped_column(String(50), primary_key=True)
    required: Mapped[bool | None] = mapped_column(default=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updated_by: Mapped["User | None"] = relationship("User")

    def __repr__(self):
        return f"<TotpRolePolicy(role={self.role}, required={self.required})>"
