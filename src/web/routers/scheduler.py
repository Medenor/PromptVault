# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Scheduler management endpoints.

Provides admin endpoints for managing background schedulers like session cleanup.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.config.auth_config import AuthConfig
from src.web.dependencies.auth import (
    get_current_active_user,
    get_admin_user,
    get_admin_or_bypass,
    get_auth_config,
)
from src.db.models.user import User
from src.scheduler.session_cleanup import SessionCleanupScheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/scheduler", tags=["admin", "scheduler"])

# Global scheduler instance (will be initialized by app)
_session_cleanup_scheduler: Optional[SessionCleanupScheduler] = None


def get_scheduler() -> SessionCleanupScheduler:
    """Get the global session cleanup scheduler instance."""
    if _session_cleanup_scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session cleanup scheduler not initialized",
        )
    return _session_cleanup_scheduler


def set_scheduler(scheduler: SessionCleanupScheduler) -> None:
    """Set the global session cleanup scheduler instance."""
    global _session_cleanup_scheduler
    _session_cleanup_scheduler = scheduler


class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status."""

    is_running: bool = Field(
        ..., description="Whether scheduler is currently running", example=True
    )
    next_run_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp of next scheduled cleanup",
        example="2025-12-06T14:00:00",
    )
    last_run_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last cleanup run",
    )
    job_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Detailed job information"
    )


class CleanupResultResponse(BaseModel):
    """Response model for cleanup operation result."""

    success: bool = Field(..., description="Whether cleanup succeeded", example=True)
    expired_found: Optional[int] = Field(
        default=None, description="Number of expired sessions found", example=42
    )
    deleted: Optional[int] = Field(
        default=None, description="Number of sessions deleted", example=42
    )
    timestamp: datetime = Field(
        ..., description="When cleanup was performed", example="2025-12-06T13:00:00"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if cleanup failed"
    )


@router.get(
    "/status",
    response_model=SchedulerStatusResponse,
    summary="Get scheduler status",
    description="Get current status of session cleanup scheduler",
)
def get_scheduler_status(
    current_user: Optional[User] = Depends(get_admin_or_bypass),
    scheduler: SessionCleanupScheduler = Depends(get_scheduler),
) -> SchedulerStatusResponse:
    """Get session cleanup scheduler status.

    Args:
        current_user: Admin user (injected)
        scheduler: Session cleanup scheduler (injected)

    Returns:
        SchedulerStatusResponse: Current scheduler status

    Requires:
        - Admin role
    """
    job_info = scheduler.get_job_info()

    return SchedulerStatusResponse(
        is_running=scheduler.is_running,
        next_run_time=job_info.get("next_run_time") if job_info else None,
        job_info=job_info,
    )


@router.post(
    "/start",
    response_model=SchedulerStatusResponse,
    summary="Start scheduler",
    description="Start the session cleanup scheduler",
)
def start_scheduler(
    current_user: Optional[User] = Depends(get_admin_or_bypass),
    scheduler: SessionCleanupScheduler = Depends(get_scheduler),
) -> SchedulerStatusResponse:
    """Start the session cleanup scheduler.

    Args:
        current_user: Admin user (injected)
        scheduler: Session cleanup scheduler (injected)

    Returns:
        SchedulerStatusResponse: Updated scheduler status

    Requires:
        - Admin role

    Raises:
        HTTPException: If scheduler is already running
    """
    if scheduler.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Scheduler is already running"
        )

    try:
        scheduler.start()
        logger.info(
            f"Scheduler started by admin user: {current_user.username if current_user else 'anonymous'}"
        )

        job_info = scheduler.get_job_info()
        return SchedulerStatusResponse(
            is_running=scheduler.is_running,
            next_run_time=job_info.get("next_run_time") if job_info else None,
            job_info=job_info,
        )
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scheduler: {str(e)}",
        )


@router.post(
    "/stop",
    response_model=SchedulerStatusResponse,
    summary="Stop scheduler",
    description="Stop the session cleanup scheduler",
)
def stop_scheduler(
    current_user: Optional[User] = Depends(get_admin_or_bypass),
    scheduler: SessionCleanupScheduler = Depends(get_scheduler),
) -> SchedulerStatusResponse:
    """Stop the session cleanup scheduler.

    Args:
        current_user: Admin user (injected)
        scheduler: Session cleanup scheduler (injected)

    Returns:
        SchedulerStatusResponse: Updated scheduler status

    Requires:
        - Admin role

    Raises:
        HTTPException: If scheduler is not running
    """
    if not scheduler.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Scheduler is not running"
        )

    try:
        scheduler.stop()
        logger.info(
            f"Scheduler stopped by admin user: {current_user.username if current_user else 'anonymous'}"
        )

        return SchedulerStatusResponse(
            is_running=scheduler.is_running,
            next_run_time=None,
            job_info=None,
        )
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop scheduler: {str(e)}",
        )


@router.post(
    "/cleanup-now",
    response_model=CleanupResultResponse,
    summary="Run cleanup now",
    description="Run session cleanup immediately (bypasses schedule)",
)
def run_cleanup_now(
    current_user: Optional[User] = Depends(get_admin_or_bypass),
    scheduler: SessionCleanupScheduler = Depends(get_scheduler),
) -> CleanupResultResponse:
    """Run session cleanup immediately.

    Useful for manual maintenance or testing.

    Args:
        current_user: Admin user (injected)
        scheduler: Session cleanup scheduler (injected)

    Returns:
        CleanupResultResponse: Cleanup operation result

    Requires:
        - Admin role
    """
    try:
        result = scheduler.run_cleanup_now()

        logger.info(
            f"Manual cleanup executed by admin user: {current_user.username if current_user else 'anonymous'}, "
            f"expired_found={result.get('expired_found')}"
        )

        return CleanupResultResponse(
            success=result.get("success", False),
            expired_found=result.get("expired_found"),
            deleted=result.get("expired_found"),
            timestamp=datetime.fromisoformat(
                result.get("timestamp", datetime.utcnow().isoformat())
            ),
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"Manual cleanup failed: {e}", exc_info=True)

        return CleanupResultResponse(
            success=False,
            timestamp=datetime.utcnow(),
            error=str(e),
        )
