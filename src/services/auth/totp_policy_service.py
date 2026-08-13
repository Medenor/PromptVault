# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin-configured per-role 2FA enforcement policy service (User Story 4).

Wraps TotpRepository's role-policy CRUD with the domain rule that an
absent row is equivalent to ``required=False`` (data-model.md, contracts
§7).
"""

import logging
from typing import Literal, cast, get_args

from src.db.repositories.totp_repository import TotpRepository

logger = logging.getLogger(__name__)

Role = Literal["viewer", "editor", "admin"]
VALID_ROLES: tuple[Role, ...] = get_args(Role)


class TotpRolePolicyEntry:
    """A single role's 2FA-required policy entry.

    Attributes:
        role: Role name
        required: Whether members of this role must have 2FA enabled
    """

    def __init__(self, role: Role, required: bool) -> None:
        self.role = role
        self.required = required


class TotpPolicyService:
    """Service for admin-managed per-role 2FA enforcement policy.

    Attributes:
        totp_repository: Repository for TotpRolePolicy persistence
    """

    def __init__(self, totp_repository: TotpRepository) -> None:
        """Initialize TotpPolicyService.

        Args:
            totp_repository: Repository for TotpRolePolicy persistence
        """
        self.totp_repository = totp_repository

    def get_all(self) -> list[TotpRolePolicyEntry]:
        """Get the 2FA-required policy for every known role.

        Roles without a configured row are reported as ``required=False``
        (data-model.md `totp_role_policies` lifecycle).

        Returns:
            One TotpRolePolicyEntry per role in VALID_ROLES
        """
        configured = {
            policy.role: bool(policy.required)
            for policy in self.totp_repository.get_all_role_policies()
        }
        return [
            TotpRolePolicyEntry(role=role, required=configured.get(role, False))
            for role in VALID_ROLES
        ]

    def set(self, role: str, required: bool, admin_user_id: str) -> TotpRolePolicyEntry:
        """Set the 2FA-required policy for a role.

        Args:
            role: Role name (must be one of VALID_ROLES)
            required: Whether members of this role must have 2FA enabled
            admin_user_id: The admin making the change (audit trail)

        Returns:
            The updated TotpRolePolicyEntry

        Raises:
            ValueError: If role is not a recognized role
        """
        if role not in VALID_ROLES:
            raise ValueError(f"Unknown role: {role}")

        policy = self.totp_repository.set_role_policy(role, required, admin_user_id)
        logger.info(
            "TOTP 2FA policy updated for role=%s required=%s by admin_user_id=%s",
            role,
            required,
            admin_user_id,
        )
        # policy.role is the DB row's plain str column; validated against
        # VALID_ROLES above, so narrowing here is a runtime-true invariant.
        return TotpRolePolicyEntry(
            role=cast(Role, policy.role), required=bool(policy.required)
        )

    def is_required_for(self, role: str) -> bool:
        """Check whether 2FA is required for a given role.

        Args:
            role: Role name

        Returns:
            True if an admin has marked this role as required, else False
            (including for unknown roles / absent policy rows)
        """
        policy = self.totp_repository.get_role_policy(role)
        return bool(policy.required) if policy is not None else False
