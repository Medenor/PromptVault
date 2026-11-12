# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TOTP two-factor authentication router (User Stories 1 and 3).

Contains the enrollment endpoints:
    POST /api/auth/2fa/enroll  - start (or restart) enrollment
    POST /api/auth/2fa/verify  - confirm enrollment with a TOTP code

And the account-lifecycle endpoints (User Story 3):
    POST /api/auth/2fa/disable                      - disable 2FA
    POST /api/auth/2fa/recovery-codes/regenerate     - regenerate recovery codes

Later phases (admin policy) extend this router — see
specs/009-totp-2fa/tasks.md T049 onward.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models.user import User
from src.db.session import get_db
from src.services.auth.totp_service import TotpService
from src.services.exceptions import (
    TotpAlreadyEnabledError,
    TotpCodeInvalidError,
    TotpEnrollmentNotFoundError,
    TotpReauthFailedError,
)
from src.services.logging_service import logging_service
from src.web.dependencies.auth import get_current_active_user
from src.web.middleware.rate_limit import expensive_limit, limiter
from src.web.models.auth_requests import TotpDisableRequest, TotpVerifyRequest
from src.web.models.auth_responses import TotpConfirmResponse, TotpEnrollResponse
from src.web.routers.auth_shared import get_totp_service

logger = logging_service.get_logger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Authentication failed - Invalid credentials or token"},
        429: {"description": "Rate limit exceeded - Too many requests"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "/2fa/enroll",
    response_model=TotpEnrollResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start TOTP 2FA enrollment",
    description="""
    Start (or restart) TOTP two-factor authentication enrollment.

    This endpoint:
    - Generates a new base32 TOTP secret
    - Builds the otpauth:// provisioning URI and an inline SVG QR code
    - Encrypts the secret at rest (AES-256-GCM, server-held key)
    - Replaces any existing pending (unconfirmed) enrollment

    The plaintext secret and QR code are returned only in this response —
    the secret is never retrievable again. Confirm enrollment via
    ``POST /api/auth/2fa/verify``.
    """,
    responses={
        201: {
            "description": "Enrollment started",
            "model": TotpEnrollResponse,
        },
        409: {
            "description": "Two-factor authentication is already enabled",
        },
    },
)
@limiter.limit(expensive_limit)
def enroll_totp(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    totp_service: TotpService = Depends(get_totp_service),
    session: Session = Depends(get_db),
) -> TotpEnrollResponse:
    """Start TOTP 2FA enrollment for the current user.

    Args:
        request: FastAPI request object (for rate limiting)
        current_user: Authenticated active user (injected)
        totp_service: TOTP 2FA service instance (injected)
        session: Database session (injected)

    Returns:
        TotpEnrollResponse: Plaintext secret, provisioning URI, and QR SVG

    Raises:
        HTTPException: 409 if 2FA is already enabled
    """
    try:
        result = totp_service.enroll(current_user)

        session.commit()

        logging_service.log_audit_event(
            action="2fa.enroll_started",
            resource_type="user",
            resource_id=current_user.id,
        )

        return TotpEnrollResponse(
            secret=result.secret,
            provisioning_uri=result.provisioning_uri,
            qr_svg=result.qr_svg,
        )

    except TotpAlreadyEnabledError as e:
        session.rollback()
        logger.info(
            f"2FA enrollment refused - already enabled for user: {current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.user_message,
        ) from e

    except IntegrityError as e:
        # Two enroll requests raced (double-click / key repeat) and the other
        # one created the pending credential first. Do not retry: replacing
        # its secret would invalidate the QR code the user already received.
        session.rollback()
        logger.info(
            f"2FA enrollment already in progress for user: {current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Two-factor enrollment is already in progress.",
        ) from e

    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error during 2FA enrollment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while starting 2FA enrollment. Please try again.",
        ) from e


@router.post(
    "/2fa/verify",
    response_model=TotpConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm TOTP 2FA enrollment",
    description="""
    Confirm a pending TOTP enrollment with a verification code.

    This endpoint:
    - Verifies the provided code against the pending credential
      (±1 time-step tolerance, FR-006)
    - Activates two-factor authentication on success
    - Issues 10 one-time recovery codes

    Recovery codes are returned only in this response — they cannot be
    retrieved again after this call (FR-003).
    """,
    responses={
        200: {
            "description": "2FA enabled; recovery codes issued",
            "model": TotpConfirmResponse,
        },
        400: {
            "description": "No pending enrollment to confirm",
        },
        401: {
            "description": "Code incorrect or outside the valid time window",
        },
    },
)
@limiter.limit(expensive_limit)
def verify_totp(
    request: Request,
    response: Response,
    request_data: TotpVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    totp_service: TotpService = Depends(get_totp_service),
    session: Session = Depends(get_db),
) -> TotpConfirmResponse:
    """Confirm TOTP 2FA enrollment for the current user.

    Args:
        request: FastAPI request object (for rate limiting)
        request_data: Verification code
        current_user: Authenticated active user (injected)
        totp_service: TOTP 2FA service instance (injected)
        session: Database session (injected)

    Returns:
        TotpConfirmResponse: Enabled flag and one-time recovery codes

    Raises:
        HTTPException: 400 if no pending enrollment, 401 if code invalid
    """
    try:
        result = totp_service.confirm(current_user, request_data.code)

        session.commit()

        logging_service.log_audit_event(
            action="2fa.enabled",
            resource_type="user",
            resource_id=current_user.id,
        )

        logger.info(f"2FA enabled successfully for user: {current_user.username}")

        return TotpConfirmResponse(
            enabled=True,
            recovery_codes=result.recovery_codes,
        )

    except TotpEnrollmentNotFoundError as e:
        session.rollback()
        logger.info(
            f"2FA confirmation failed - no pending enrollment for user: {current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.user_message,
        ) from e

    except TotpCodeInvalidError as e:
        session.rollback()
        logger.info(
            f"2FA confirmation failed - invalid code for user: {current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except Exception as e:
        session.rollback()
        logger.error(
            f"Unexpected error during 2FA confirmation: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while confirming 2FA. Please try again.",
        ) from e


@router.post(
    "/2fa/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disable TOTP 2FA",
    description="""
    Disable two-factor authentication, re-authenticated with the current
    password plus a current TOTP or recovery code.

    On success, the TOTP credential and all recovery codes are deleted.
    Failures are reported generically (does not reveal which factor was
    wrong).
    """,
    responses={
        204: {"description": "2FA disabled"},
        401: {"description": "Incorrect password or authentication code"},
    },
)
@limiter.limit(expensive_limit)
def disable_totp(
    request: Request,
    response: Response,
    request_data: TotpDisableRequest,
    current_user: User = Depends(get_current_active_user),
    totp_service: TotpService = Depends(get_totp_service),
    session: Session = Depends(get_db),
) -> None:
    """Disable TOTP 2FA for the current user.

    Args:
        request: FastAPI request object (for rate limiting)
        request_data: Current password and TOTP/recovery code
        current_user: Authenticated active user (injected)
        totp_service: TOTP 2FA service instance (injected)
        session: Database session (injected)

    Raises:
        HTTPException: 401 if password or code is incorrect
    """
    try:
        totp_service.disable(current_user, request_data.password, request_data.code)

        session.commit()

        logging_service.log_audit_event(
            action="2fa.disabled",
            resource_type="user",
            resource_id=current_user.id,
        )

        logger.info(f"2FA disabled successfully for user: {current_user.username}")

    except TotpReauthFailedError as e:
        session.rollback()
        logger.info(
            f"2FA disable failed - re-auth failed for user: {current_user.username}"
        )
        logging_service.log_audit_event(
            action="2fa.disable_failed",
            resource_type="user",
            resource_id=current_user.id,
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error while disabling 2FA: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while disabling 2FA. Please try again.",
        ) from e


@router.post(
    "/2fa/recovery-codes/regenerate",
    response_model=TotpConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate TOTP recovery codes",
    description="""
    Regenerate recovery codes, re-authenticated with the current password
    plus a current TOTP or recovery code.

    All previously issued codes are invalidated in the same transaction.
    Failures are reported generically (does not reveal which factor was
    wrong).
    """,
    responses={
        200: {
            "description": "New recovery codes issued",
            "model": TotpConfirmResponse,
        },
        401: {"description": "Incorrect password or authentication code"},
    },
)
@limiter.limit(expensive_limit)
def regenerate_totp_recovery_codes(
    request: Request,
    response: Response,
    request_data: TotpDisableRequest,
    current_user: User = Depends(get_current_active_user),
    totp_service: TotpService = Depends(get_totp_service),
    session: Session = Depends(get_db),
) -> TotpConfirmResponse:
    """Regenerate TOTP recovery codes for the current user.

    Args:
        request: FastAPI request object (for rate limiting)
        request_data: Current password and TOTP/recovery code
        current_user: Authenticated active user (injected)
        totp_service: TOTP 2FA service instance (injected)
        session: Database session (injected)

    Returns:
        TotpConfirmResponse: New one-time plaintext recovery codes

    Raises:
        HTTPException: 401 if password or code is incorrect
    """
    try:
        result = totp_service.regenerate_recovery_codes(
            current_user, request_data.password, request_data.code
        )

        session.commit()

        logging_service.log_audit_event(
            action="2fa.recovery_codes_regenerated",
            resource_type="user",
            resource_id=current_user.id,
        )

        logger.info(f"2FA recovery codes regenerated for user: {current_user.username}")

        return TotpConfirmResponse(
            enabled=True,
            recovery_codes=result.recovery_codes,
        )

    except TotpReauthFailedError as e:
        session.rollback()
        logger.info(
            f"2FA recovery-code regeneration failed - re-auth failed for user: {current_user.username}"
        )
        logging_service.log_audit_event(
            action="2fa.recovery_codes_regenerate_failed",
            resource_type="user",
            resource_id=current_user.id,
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except Exception as e:
        session.rollback()
        logger.error(
            f"Unexpected error while regenerating 2FA recovery codes: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while regenerating recovery codes. Please try again.",
        ) from e
