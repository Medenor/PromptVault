# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin TOTP 2FA enforcement policy routes for PromptVault (User Story 4).

Available Endpoints:
    GET /admin/2fa/policy    List 2FA-required policy for every role
    PUT /admin/2fa/policy    Set 2FA-required policy for a role

All endpoints require the admin role and are audit logged.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.models.user import User
from src.db.session import get_db
from src.services.auth.totp_policy_service import TotpPolicyService
from src.web.dependencies.auth import require_role
from src.web.models.auth_requests import TotpPolicyUpdateRequest
from src.web.models.auth_responses import TotpPolicyResponse, TotpRolePolicyItem
from src.web.routers.admin_shared import _log_admin_action
from src.web.routers.auth_shared import get_totp_policy_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get(
    "/2fa/policy",
    response_model=TotpPolicyResponse,
    summary="Get 2FA-required policy for every role",
    description="""
    Get the admin-configured 2FA-required policy for every role.

    Roles without an explicit policy row are reported as `required: false`.

    **Security:**
    - Requires admin role
    - Audit logged
    """,
    responses={
        200: {"description": "Policy retrieved successfully"},
        403: {"description": "Admin role required"},
    },
)
def get_totp_policy(
    admin: User = Depends(require_role(["admin"])),
    totp_policy_service: TotpPolicyService = Depends(get_totp_policy_service),
) -> TotpPolicyResponse:
    """Get the 2FA-required policy for every role.

    Args:
        admin: Authenticated admin user (injected)
        totp_policy_service: TOTP policy service instance (injected)

    Returns:
        TotpPolicyResponse: Policy entry for every role
    """
    entries = totp_policy_service.get_all()

    _log_admin_action(
        admin.id,
        admin.username,
        "VIEW_2FA_POLICY",
        "N/A",
    )

    return TotpPolicyResponse(
        roles=[
            TotpRolePolicyItem(role=entry.role, required=entry.required)
            for entry in entries
        ]
    )


@router.put(
    "/2fa/policy",
    response_model=TotpRolePolicyItem,
    summary="Set 2FA-required policy for a role",
    description="""
    Set whether members of a role must have 2FA enabled.

    Enforcement (FR-015) is evaluated at login: users in a `required=true`
    role without `totp_enabled=True` receive `enrollment_required: true`
    alongside their normal login response, and the frontend routes them
    into mandatory enrollment before granting access to other
    functionality.

    **Security:**
    - Requires admin role
    - Audit logged
    """,
    responses={
        200: {"description": "Policy updated successfully"},
        403: {"description": "Admin role required"},
        422: {"description": "Unknown role value"},
    },
)
def set_totp_policy(
    request_data: TotpPolicyUpdateRequest,
    admin: User = Depends(require_role(["admin"])),
    totp_policy_service: TotpPolicyService = Depends(get_totp_policy_service),
    session: Session = Depends(get_db),
) -> TotpRolePolicyItem:
    """Set the 2FA-required policy for a role.

    Args:
        request_data: Role and required flag
        admin: Authenticated admin user (injected)
        totp_policy_service: TOTP policy service instance (injected)
        session: Database session (injected)

    Returns:
        TotpRolePolicyItem: The updated policy entry
    """
    entry = totp_policy_service.set(request_data.role, request_data.required, admin.id)
    session.commit()

    _log_admin_action(
        admin.id,
        admin.username,
        "UPDATE_2FA_POLICY",
        "N/A",
        f"role={request_data.role}, required={request_data.required}",
    )

    return TotpRolePolicyItem(role=entry.role, required=entry.required)
