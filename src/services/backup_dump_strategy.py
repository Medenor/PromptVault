# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Database-specific dump/restore mechanics for BackupService.

Each DumpStrategy knows how to physically create a backup file for its
database engine and how to physically restore the live database from one.
Everything else (metadata, encryption, compression, audit logging) is
handled by the callers in backup_creation_service.py / backup_restore_service.py
so it stays identical across engines.
"""

import os
import subprocess
from typing import Protocol, Tuple

from src.db.config import db_settings
from src.services.exceptions import BackupError
from src.services.logging_service import logging_service

logger = logging_service.get_logger(__name__)


class DumpStrategy(Protocol):
    """Creates and restores a single database engine's backup files."""

    def dump(self, backup_path: str) -> None:
        """Write a backup of the live database to backup_path."""
        ...

    def restore(self, backup_id: str, backup_path: str) -> bool:
        """Overwrite the live database with the contents of backup_path."""
        ...


def _resolve_sqlite_db_path() -> str:
    db_url = db_settings.DATABASE_URL
    if not db_url.startswith("sqlite:///"):
        raise BackupError(
            "Invalid SQLite DATABASE_URL format",
            context={"database_url": db_url},
        )
    db_path = db_url.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        script_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        db_path = os.path.join(script_dir, db_path)
    return db_path


class SqliteDumpStrategy:
    """SQLite backup via VACUUM INTO, restore via the online backup API."""

    def dump(self, backup_path: str) -> None:
        import sqlite3

        db_path = _resolve_sqlite_db_path()
        if not os.path.exists(db_path):
            raise BackupError(
                "Database file does not exist",
                context={"db_path": db_path},
                http_status=404,
            )

        # Use VACUUM INTO rather than a raw file copy so the backup
        # excludes free/unused pages left behind by deletes (e.g. after
        # session cleanup sweeps). A plain shutil.copy2 would faithfully
        # copy the live file's high-water-mark size, including pages
        # SQLite has freed but not reclaimed.
        source_conn = sqlite3.connect(db_path)
        try:
            source_conn.execute("VACUUM INTO ?", (backup_path,))
        finally:
            source_conn.close()

    def restore(self, backup_id: str, backup_path: str) -> bool:
        try:
            import sqlite3
            from src.db.session import engine

            db_path = _resolve_sqlite_db_path()

            # Use SQLite's online backup API to safely replace the live
            # database. This avoids the corruption risk of a raw file copy
            # while connections are open and properly handles WAL/SHM state.
            engine.dispose()

            src_conn = sqlite3.connect(backup_path)
            dst_conn = sqlite3.connect(db_path)
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
                src_conn.close()

            logger.info(
                "SQLite database restored from backup",
                extra={"event": "backup.restore.success", "backup_id": backup_id},
            )
            return True

        except Exception as exc:
            logger.error(
                "Failed to restore SQLite backup",
                extra={"event": "backup.restore.failure", "backup_id": backup_id},
                exc_info=exc,
            )
            raise BackupError(
                "Failed to restore SQLite backup.", context={"backup_id": backup_id}
            ) from exc


class PostgresDumpStrategy:
    """PostgreSQL backup/restore via the pg_dump/psql CLI tools."""

    def dump(self, backup_path: str) -> None:
        db_url = db_settings.DATABASE_URL
        cmd = [
            "pg_dump",
            "--file",
            backup_path,
            "--format=plain",
            "--clean",
            "--if-exists",
            db_url,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr if exc.stderr else str(exc)
            logger.error(
                "pg_dump failed",
                extra={"event": "backup.create.failure", "error": error_msg},
                exc_info=exc,
            )
            raise BackupError(f"pg_dump failed: {error_msg}") from exc

    def restore(self, backup_id: str, backup_path: str) -> bool:
        try:
            db_url = db_settings.DATABASE_URL
            cmd = ["psql", "--file", backup_path, db_url]
            subprocess.run(cmd, check=True, capture_output=True, text=True)

            logger.info(
                "PostgreSQL database restored from backup",
                extra={"event": "backup.restore.success", "backup_id": backup_id},
            )
            return True

        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr if exc.stderr else str(exc)
            logger.error(
                "psql restore failed",
                extra={
                    "event": "backup.restore.failure",
                    "backup_id": backup_id,
                    "error": error_msg,
                },
                exc_info=exc,
            )
            raise BackupError(
                f"psql restore failed: {error_msg}", context={"backup_id": backup_id}
            ) from exc
        except Exception as exc:
            logger.error(
                "Failed to restore PostgreSQL backup",
                extra={"event": "backup.restore.failure", "backup_id": backup_id},
                exc_info=exc,
            )
            raise BackupError(
                "Failed to restore PostgreSQL backup.", context={"backup_id": backup_id}
            ) from exc


def get_dump_strategy() -> Tuple[str, "DumpStrategy"]:
    """Return (backup_type, strategy) for the currently configured database."""
    if db_settings.is_sqlite:
        return "sqlite_copy", SqliteDumpStrategy()
    if db_settings.is_postgresql:
        return "pg_dump", PostgresDumpStrategy()
    raise BackupError(
        "Unsupported database type",
        context={"database_url": db_settings.DATABASE_URL},
    )
