# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup audit service for PromptVault.

Provides audit logging and monitoring dashboard statistics for all
backup-related operations.
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import func

from src.db.session import get_db_session
from src.db.models import Backup
from src.db.models.backup_audit_log import AuditLogEntry
from src.db.repositories.backup_audit_log_repository import BackupAuditLogRepository

logger = logging.getLogger(__name__)


def _isoformat_utc(dt: Optional[datetime]) -> Optional[str]:
    """Serialize a datetime as ISO-8601 with explicit UTC offset.

    SQLite's func.now() (and DateTime(timezone=True) columns generally on
    SQLite) yield naive datetimes that are actually UTC but carry no tzinfo,
    so a plain isoformat() omits the offset and browsers misinterpret it as
    local time.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class BackupAuditService:
    """Service for backup audit logging and monitoring.

    Records all backup operations and provides dashboard statistics.
    """

    def log(
        self,
        operation: str,
        outcome: str,
        backup_id: Optional[str] = None,
        performed_by: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an audit log entry.

        Args:
            operation: Operation type (e.g. 'backup.create', 'backup.restore')
            outcome: 'success' or 'failure'
            backup_id: Associated backup ID
            performed_by: Username or 'scheduler'
            detail: Additional context
        """
        try:
            with get_db_session() as session:
                repo = BackupAuditLogRepository(session)
                repo.append(
                    id=str(uuid.uuid4()),
                    operation=operation,
                    outcome=outcome,
                    backup_id=backup_id,
                    performed_by=performed_by,
                    detail=detail,
                )
                session.commit()
        except Exception as exc:
            logger.warning(
                "Failed to write audit log entry",
                extra={"event": "audit.write_failure", "operation": operation},
                exc_info=exc,
            )

    def get_log(
        self,
        operation: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get paginated audit log entries.

        Args:
            operation: Filter by operation type
            outcome: Filter by outcome
            limit: Max results
            offset: Offset for pagination

        Returns:
            Dict with 'entries' list and 'total' count
        """
        with get_db_session() as session:
            repo = BackupAuditLogRepository(session)
            entries = repo.list_entries(
                operation=operation, outcome=outcome, limit=limit, offset=offset
            )
            total = repo.count_with_filters(operation=operation, outcome=outcome)

            return {
                "entries": [self._serialize_entry(e) for e in entries],
                "total": total,
            }

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Compute monitoring dashboard statistics.

        Returns:
            Dict with total_backups, success_rate_30d, total_size_bytes,
            last_backup_at, last_backup_status, quota_warning, history
        """
        with get_db_session() as session:
            total_backups = session.query(Backup).count()

            total_size = (
                session.query(func.coalesce(func.sum(Backup.size_bytes), 0)).scalar() or 0
            )

            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            recent = (
                session.query(Backup)
                .filter(Backup.created_at >= thirty_days_ago)
                .all()
            )
            successful_30d = sum(1 for b in recent if b.succeeded)
            success_rate = successful_30d / len(recent) if recent else 1.0

            last_backup = (
                session.query(Backup)
                .order_by(Backup.created_at.desc())
                .first()
            )

            history = self._compute_history(session)

            storage_quota = 10 * 1024 * 1024 * 1024
            quota_warning = total_size > storage_quota * 0.9

            return {
                "total_backups": total_backups,
                "success_rate_30d": round(success_rate, 2),
                "total_size_bytes": total_size,
                "storage_quota_bytes": storage_quota,
                "quota_warning": quota_warning,
                "last_backup_at": (
                    _isoformat_utc(last_backup.created_at) if last_backup else None
                ),
                "last_backup_status": (
                    "success" if last_backup and last_backup.succeeded else "failure"
                    if last_backup else None
                ),
                "history": history,
            }

    @staticmethod
    def _compute_history(session) -> List[Dict[str, Any]]:
        """Compute per-day backup history for last 30 days."""
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        backups = (
            session.query(Backup)
            .filter(Backup.created_at >= thirty_days_ago)
            .order_by(Backup.created_at.asc())
            .all()
        )

        day_map: Dict[str, Dict[str, Any]] = {}
        for b in backups:
            if b.created_at:
                day_key = b.created_at.strftime("%Y-%m-%d")
                if day_key not in day_map:
                    day_map[day_key] = {"date": day_key, "count": 0, "success": 0, "failure": 0, "total_size_bytes": 0}
                day_map[day_key]["count"] += 1
                if b.succeeded:
                    day_map[day_key]["success"] += 1
                else:
                    day_map[day_key]["failure"] += 1
                day_map[day_key]["total_size_bytes"] += b.size_bytes or 0

        return sorted(day_map.values(), key=lambda x: x["date"])

    @staticmethod
    def _serialize_entry(entry: AuditLogEntry) -> Dict[str, Any]:
        """Serialize an audit log entry to dict."""
        return {
            "id": entry.id,
            "occurred_at": _isoformat_utc(entry.occurred_at),
            "operation": entry.operation,
            "outcome": entry.outcome,
            "backup_id": entry.backup_id,
            "performed_by": entry.performed_by,
            "detail": entry.detail,
        }
