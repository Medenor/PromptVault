# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Startup and shutdown lifecycle events for the PromptVault FastAPI app.

Owns the session-cleanup scheduler's lifecycle so `app.py` doesn't need to
know how it's constructed or torn down.
"""

from fastapi import FastAPI

from src.services.logging_service import logging_service

logger = logging_service.get_logger(__name__)

_session_cleanup_scheduler = None


def register_lifecycle_events(app: FastAPI) -> None:
    """Register startup/shutdown handlers that manage the session cleanup
    scheduler and load persisted backup schedule jobs.
    """

    @app.on_event("startup")
    async def startup_scheduler():
        """Initialize and start the session cleanup scheduler on app startup."""
        global _session_cleanup_scheduler

        try:
            from src.config.auth_config import auth_settings
            from src.db.session import SessionLocal
            from src.scheduler.session_cleanup import SessionCleanupScheduler
            from src.web.routers.scheduler import set_scheduler

            # Create scheduler instance
            _session_cleanup_scheduler = SessionCleanupScheduler(
                session_factory=SessionLocal,
                config=auth_settings,
                cleanup_interval_hours=auth_settings.cleanup_interval_hours,
                batch_size=auth_settings.cleanup_batch_size,
            )

            # Register with router for dependency injection
            set_scheduler(_session_cleanup_scheduler)

            # Start the scheduler
            _session_cleanup_scheduler.start()

            # Run an immediate sweep so expired sessions don't accumulate when the
            # process restarts before the first scheduled interval elapses (common
            # in dev, where the app rarely stays up for a full cleanup_interval_hours).
            startup_cleanup_result = _session_cleanup_scheduler.run_cleanup_now()
            logger.info(
                "✓ Startup session cleanup sweep completed "
                f"(deleted: {startup_cleanup_result.get('deleted', 0)})"
            )

            logger.info(
                "✓ Session cleanup scheduler initialized and started "
                f"(interval: {auth_settings.cleanup_interval_hours}h, "
                f"batch_size: {auth_settings.cleanup_batch_size})"
            )

        except ImportError as e:
            logger.warning(f"Scheduler imports not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}", exc_info=True)

        try:
            from src.scheduler.backup_scheduler import register_backup_jobs

            register_backup_jobs()
            logger.info("✓ Backup schedule loaded and registered from database")
        except Exception as e:
            logger.error(f"Failed to register backup jobs: {e}", exc_info=True)

    @app.on_event("shutdown")
    async def shutdown_scheduler():
        """Gracefully shutdown the session cleanup scheduler on app shutdown."""
        global _session_cleanup_scheduler

        if _session_cleanup_scheduler is not None:
            try:
                _session_cleanup_scheduler.stop()
                logger.info("✓ Session cleanup scheduler stopped gracefully")
            except Exception as e:
                logger.error(f"Error stopping scheduler: {e}", exc_info=True)
