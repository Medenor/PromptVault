# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Sharing repository for PromptVault.

Data access layer for PromptShare — per-prompt sharing grants between users.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.db.models import PromptShare
from src.db.repositories.base import BaseRepository


class SharingRepository(BaseRepository[PromptShare]):
    """Repository for PromptShare grants.

    Provides create-or-update-in-place (upsert), revocation, and the two
    lookup directions (by prompt, by grantee) needed for grant review and
    visibility scoping.
    """

    def __init__(self, session: Session):
        """Initialize SharingRepository.

        Args:
            session: Database session
        """
        super().__init__(PromptShare, session)

    def upsert(
        self,
        prompt_id: int,
        grantee_user_id: str,
        permission: str,
        granted_by: Optional[str],
    ) -> PromptShare:
        """Create a grant, or update its permission in place if one exists.

        Args:
            prompt_id: Prompt being shared
            grantee_user_id: User receiving access
            permission: 'read' or 'edit'
            granted_by: User id creating/updating the grant (may be None)

        Returns:
            The created or updated PromptShare
        """
        existing = (
            self.session.query(PromptShare)
            .filter(
                PromptShare.prompt_id == prompt_id,
                PromptShare.grantee_user_id == grantee_user_id,
            )
            .first()
        )
        if existing:
            existing.permission = permission
            existing.granted_by = granted_by
            self.session.flush()
            return existing

        share = PromptShare(
            prompt_id=prompt_id,
            grantee_user_id=grantee_user_id,
            permission=permission,
            granted_by=granted_by,
        )
        self.session.add(share)
        self.session.flush()
        return share

    def revoke(self, prompt_id: int, grantee_user_id: str) -> bool:
        """Revoke a grant.

        Args:
            prompt_id: Prompt the grant belongs to
            grantee_user_id: Grantee whose access is being revoked

        Returns:
            True if a grant was found and removed, False otherwise
        """
        existing = (
            self.session.query(PromptShare)
            .filter(
                PromptShare.prompt_id == prompt_id,
                PromptShare.grantee_user_id == grantee_user_id,
            )
            .first()
        )
        if not existing:
            return False
        self.session.delete(existing)
        self.session.flush()
        return True

    def list_for_prompt(self, prompt_id: int) -> List[PromptShare]:
        """List all grants on a prompt (grant review).

        Args:
            prompt_id: Prompt to list grants for

        Returns:
            List of PromptShare grants
        """
        return (
            self.session.query(PromptShare)
            .filter(PromptShare.prompt_id == prompt_id)
            .all()
        )

    def list_for_grantee(self, user_id: str) -> List[PromptShare]:
        """List all grants made to a user.

        Args:
            user_id: Grantee user id

        Returns:
            List of PromptShare grants
        """
        return (
            self.session.query(PromptShare)
            .filter(PromptShare.grantee_user_id == user_id)
            .all()
        )

    def count_all(self) -> int:
        """Count all active sharing grants across every prompt.

        Used to warn operators before destructive operations (e.g. a
        REPLACE-mode import) that would cascade-delete every grant.

        Returns:
            Total number of PromptShare rows currently in the database
        """
        return self.session.query(PromptShare).count()

    def permission_for(self, prompt_id: int, user_id: str) -> Optional[str]:
        """Get the effective grant permission for a (prompt, user) pair.

        Hot path for authorization checks.

        Args:
            prompt_id: Prompt id
            user_id: User id

        Returns:
            'read' or 'edit' if a grant exists, otherwise None
        """
        share = (
            self.session.query(PromptShare)
            .filter(
                PromptShare.prompt_id == prompt_id,
                PromptShare.grantee_user_id == user_id,
            )
            .first()
        )
        return share.permission if share else None
