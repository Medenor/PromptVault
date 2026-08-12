# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Session cleanup scheduler service.

Provides scheduled cleanup of expired sessions using APScheduler.
Automatically removes sessions that have passed their expiration date.

Example:
    >>> from src.scheduler.session_cleanup import SessionCleanupScheduler
    >>> from src.db.session import SessionLocal
    >>> from src.config.auth_config import AuthConfig
    >>>
    >>> scheduler = SessionCleanupScheduler(
    ...     session_factory=SessionLocal,
    ...     config=AuthConfig()
    ... )
    >>> scheduler.start()
    >>> # Cleanup runs every hour
    >>> scheduler.stop()
"""

import logging
from collections.abc import Callable
from datetime import datetime

from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

from src.config.auth_config import AuthConfig
from src.db.models.user_session import UserSession
from src.db.session import SessionLocal

logger = logging.getLogger(__name__)


class SessionCleanupScheduler:
    """Scheduled cleanup of expired user sessions.

    This scheduler automatically removes sessions that have expired.
    It runs on a configurable interval (default: every hour).

    Features:
    - Background scheduling with APScheduler
    - Configurable cleanup interval
    - Detailed logging of cleanup operations
    - Graceful start/stop
    - Job status tracking

    Attributes:
        scheduler: APScheduler BackgroundScheduler instance
        config: Authentication configuration with cleanup settings
        session_factory: Database session factory
        repo: Session repository for data access
        cleanup_interval_hours: How often to run cleanup (default: 1)
        batch_size: How many sessions to clean per batch (default: 100)
        is_running: Whether scheduler is currently active
    """

    # Default configuration
    DEFAULT_CLEANUP_INTERVAL_HOURS = 1
    DEFAULT_BATCH_SIZE = 100

    def __init__(
        self,
        session_factory: Callable = SessionLocal,
        config: AuthConfig | None = None,
        cleanup_interval_hours: int = DEFAULT_CLEANUP_INTERVAL_HOURS,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        """Initialize the session cleanup scheduler.

        Args:
            session_factory: Callable that creates database sessions
            config: Authentication configuration
            cleanup_interval_hours: Interval between cleanups (hours)
            batch_size: Number of sessions to delete per batch
        """
        self.session_factory = session_factory
        self.config = config or AuthConfig()
        self.cleanup_interval_hours = cleanup_interval_hours
        self.batch_size = batch_size
        self.is_running = False
        self.current_job: Job | None = None

        # Initialize scheduler
        self.scheduler = BackgroundScheduler(daemon=True)
        self.scheduler.configure(job_defaults={"coalesce": True, "max_instances": 1})

        logger.info(
            f"SessionCleanupScheduler initialized: "
            f"interval={cleanup_interval_hours}h, batch_size={batch_size}"
        )

    def start(self) -> None:
        """Start the session cleanup scheduler.

        Raises:
            RuntimeError: If scheduler is already running

        Example:
            >>> scheduler = SessionCleanupScheduler()
            >>> scheduler.start()
            >>> # Cleanup now runs every hour
        """
        if self.is_running:
            logger.warning("Scheduler already running, ignoring start request")
            return

        try:
            self.scheduler.start()
            self.current_job = self.scheduler.add_job(
                self._cleanup_expired_sessions,
                IntervalTrigger(hours=self.cleanup_interval_hours),
                id="session-cleanup",
                name="Clean up expired sessions",
                replace_existing=True,
            )
            self.is_running = True

            logger.info(
                f"Session cleanup scheduler started: "
                f"next run in {self.cleanup_interval_hours} hour(s)"
            )
        except Exception as e:
            logger.error(f"Failed to start cleanup scheduler: {e}", exc_info=True)
            self.is_running = False
            raise RuntimeError(f"Failed to start scheduler: {e}") from e

    def stop(self) -> None:
        """Stop the session cleanup scheduler.

        Removes the cleanup job and stops the scheduler.

        Example:
            >>> scheduler = SessionCleanupScheduler()
            >>> scheduler.start()
            >>> scheduler.stop()
            >>> # Cleanup no longer runs
        """
        if not self.is_running:
            logger.warning("Scheduler not running, ignoring stop request")
            return

        try:
            if self.current_job:
                self.scheduler.remove_job(self.current_job.id)
                self.current_job = None

            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)

            self.is_running = False
            logger.info("Session cleanup scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping cleanup scheduler: {e}", exc_info=True)
            self.is_running = False

    def _cleanup_expired_sessions(self) -> dict:
        """Internal method to perform session cleanup.

        This method:
        1. Finds all expired sessions
        2. Deletes them in batches
        3. Logs cleanup statistics

        Called automatically by scheduler at configured interval.

        Returns:
            Dict with expired_found and deleted counts.
        """
        session = None
        try:
            session = self.session_factory()

            # Count expired sessions before cleanup
            now = datetime.utcnow()
            expired_sessions = session.execute(
                text("SELECT id FROM user_sessions WHERE expires_at < :now"),
                {"now": now},
            ).fetchall()

            expired_count = len(expired_sessions)
            if expired_count == 0:
                logger.debug("No expired sessions to clean up")
                return {"expired_found": 0, "deleted": 0}

            # Delete expired sessions in batches
            deleted_count = 0
            for i in range(0, expired_count, self.batch_size):
                batch_ids = [
                    row[0] for row in expired_sessions[i : i + self.batch_size]
                ]

                # Delete sessions by ID
                deleted_in_batch = (
                    session.query(UserSession)
                    .filter(UserSession.id.in_(batch_ids))
                    .delete(synchronize_session=False)
                )
                deleted_count += deleted_in_batch
                session.commit()

            # Log cleanup statistics
            duration = (datetime.utcnow() - now).total_seconds()
            logger.info(
                f"Session cleanup completed: "
                f"found={expired_count}, deleted={deleted_count}, "
                f"duration={duration:.2f}s"
            )

            return {"expired_found": expired_count, "deleted": deleted_count}

        finally:
            if session:
                session.close()

    def get_job_info(self) -> dict | None:
        """Get information about the current cleanup job.

        Returns:
            Dict with job info (next_run_time, etc.) or None if not running

        Example:
            >>> scheduler = SessionCleanupScheduler()
            >>> scheduler.start()
            >>> info = scheduler.get_job_info()
            >>> info['next_run_time']
        """
        if not self.current_job or not self.is_running:
            return None

        return {
            "id": self.current_job.id,
            "name": self.current_job.name,
            "next_run_time": self.current_job.next_run_time,
            "trigger": str(self.current_job.trigger),
        }

    def run_cleanup_now(self) -> dict:
        """Run cleanup immediately (bypasses schedule).

        Useful for testing or manual maintenance.

        Returns:
            Dict with cleanup statistics

        Example:
            >>> scheduler = SessionCleanupScheduler()
            >>> result = scheduler.run_cleanup_now()
            >>> result['deleted']
        """
        try:
            stats = self._cleanup_expired_sessions()

            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                **stats,
            }

        except Exception as e:
            logger.error(f"Error in manual cleanup: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
