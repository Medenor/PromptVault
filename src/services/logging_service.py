# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Logging utilities providing structured JSON output, rotating file handlers, and
request context propagation for PromptVault.
"""

import json
import logging
import logging.config
import os
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional, Tuple

# pylint: disable=too-many-instance-attributes


def _utc_timestamp() -> str:
    """Return the current UTC timestamp with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


REQUEST_ID_VAR: ContextVar[Optional[str]] = ContextVar(
    "promptvault_request_id", default=None
)
ACTOR_VAR: ContextVar[Optional[str]] = ContextVar("promptvault_actor", default=None)


class JsonLogFormatter(logging.Formatter):
    """Formatter that emits structured JSON for log aggregation."""

    COMMON_FIELDS = (
        "event",
        "action",
        "resource_id",
        "status",
        "duration_ms",
        "client",
        "prompt_id",
        "backup_id",
        "resource_type",
        "compressed_count",
        "removed_count",
        "format",
        "mode",
        "imported_count",
        "added_count",
        "title",
        "error_message",
        "stacktrace",
        "version_id",
        "commit_message",
    )

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the record into a JSON string including context variables.

        Args:
            record: Logging record to format.

        Returns:
            str: JSON-encoded log line.
        """
        payload: Dict[str, Optional[str]] = {
            "timestamp": _utc_timestamp(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or REQUEST_ID_VAR.get(),
            "actor": getattr(record, "actor", None) or ACTOR_VAR.get(),
        }

        for field in self.COMMON_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        reserved_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }
        for key, value in record.__dict__.items():
            if (
                key not in payload
                and key not in reserved_attrs
                and not key.startswith("_")
            ):
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for developer-friendly console logs."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log records for console output including context highlights.

        Args:
            record: Logging record to format.

        Returns:
            str: Console-friendly string.
        """
        request_id = getattr(record, "request_id", None) or REQUEST_ID_VAR.get()
        actor = getattr(record, "actor", None) or ACTOR_VAR.get()
        extras = []
        if request_id:
            extras.append(f"req={request_id}")
        if actor:
            extras.append(f"actor={actor}")
        if getattr(record, "event", None):
            extras.append(f"event={record.event}")
        if getattr(record, "status", None):
            extras.append(f"status={record.status}")

        extra_str = f" ({', '.join(extras)})" if extras else ""
        base = f"[{record.levelname}] {record.getMessage()}{extra_str}"

        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"

        return base


class LoggingService:
    """Configure and expose centralized structured logging for the app."""

    APP_LOGGER_NAME = "promptvault"
    AUDIT_LOGGER_NAME = "promptvault.audit"

    def __init__(self) -> None:
        """Initialize the logging service."""
        self._configured = False
        self._log_dir: Optional[str] = None

    def configure_logging(
        self,
        log_dir: Optional[str] = None,
        *,
        environment: Optional[str] = None,
        log_level: Optional[str] = None,
        audit_log_level: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """
        Configure the logging stack with rotating file handlers and JSON format.

        Args:
            log_dir: Directory where log files should be written.
            environment: Optional environment name (development/production/etc.).
            log_level: Override for application log level.
            audit_log_level: Override for audit log level.
            force: When True, reconfigure even if already configured (for tests).
        """
        if self._configured and not force:
            return

        env = (environment or os.getenv("ENVIRONMENT", "development")).strip()
        resolved_dir = log_dir or os.path.join(os.getcwd(), "data", "logs")
        os.makedirs(resolved_dir, exist_ok=True)

        app_level = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
        audit_level = (audit_log_level or os.getenv("AUDIT_LOG_LEVEL", "INFO")).upper()
        console_level = "DEBUG" if env == "development" else app_level

        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "src.services.logging_service.JsonLogFormatter",
                },
                "console": {
                    "()": "src.services.logging_service.ConsoleFormatter",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": console_level,
                    "formatter": "console",
                },
                "app_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": os.path.join(resolved_dir, "app.log"),
                    "maxBytes": 10 * 1024 * 1024,
                    "backupCount": 5,
                    "encoding": "utf-8",
                    "formatter": "json",
                    "level": app_level,
                },
                "audit_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": os.path.join(resolved_dir, "audit.log"),
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 10,
                    "encoding": "utf-8",
                    "formatter": "json",
                    "level": audit_level,
                },
            },
            "loggers": {
                self.APP_LOGGER_NAME: {
                    "handlers": ["console", "app_file"],
                    "level": app_level,
                    "propagate": False,
                },
                self.AUDIT_LOGGER_NAME: {
                    "handlers": ["console", "audit_file"],
                    "level": audit_level,
                    "propagate": False,
                },
            },
        }

        logging.config.dictConfig(config)
        self._configured = True
        self._log_dir = resolved_dir

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        Retrieve a logger rooted under the PromptVault namespace.

        Args:
            name: Optional suffix or fully qualified logger name.

        Returns:
            logging.Logger: Configured logger instance.
        """
        if not name:
            return logging.getLogger(self.APP_LOGGER_NAME)

        if name.startswith(self.APP_LOGGER_NAME):
            full_name = name
        else:
            sanitized = name.replace(" ", "_")
            full_name = f"{self.APP_LOGGER_NAME}.{sanitized}"
        return logging.getLogger(full_name)

    def get_audit_logger(self) -> logging.Logger:
        """
        Retrieve the audit logger dedicated to compliance events.

        Returns:
            logging.Logger: Audit logger instance.
        """
        return logging.getLogger(self.AUDIT_LOGGER_NAME)

    def generate_request_id(self) -> str:
        """
        Generate a UUID-based request identifier for correlation.

        Returns:
            str: Hex-encoded request ID.
        """
        return uuid.uuid4().hex

    @contextmanager
    def request_context(
        self, *, request_id: Optional[str] = None, actor: Optional[str] = None
    ) -> Iterator[None]:
        """
        Bind request context variables for the duration of the context manager.

        Args:
            request_id: Correlation identifier to bind.
            actor: Actor identifier associated with the operation.
        """
        tokens: Tuple[Tuple[ContextVar[Optional[str]], object], ...] = tuple()
        if request_id or actor:
            collected = []
            if request_id is not None:
                collected.append((REQUEST_ID_VAR, REQUEST_ID_VAR.set(request_id)))
            if actor is not None:
                collected.append((ACTOR_VAR, ACTOR_VAR.set(actor)))
            tokens = tuple(collected)
        try:
            yield
        finally:
            for var, token in reversed(tokens):
                var.reset(token)

    def get_request_id(self) -> Optional[str]:
        """
        Return the currently bound request ID, if any.

        Returns:
            Optional[str]: Active request identifier.
        """
        return REQUEST_ID_VAR.get()

    def get_actor(self) -> Optional[str]:
        """
        Return the currently bound actor identifier, if any.

        Returns:
            Optional[str]: Active actor identifier.
        """
        return ACTOR_VAR.get()

    def log_audit_event(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str = "success",
        event: Optional[str] = None,
        message: Optional[str] = None,
        **context: Any,
    ) -> None:
        """
        Emit a structured audit log entry for compliance-sensitive operations.

        Args:
            action: Domain-specific action name (e.g., prompt.create).
            resource_type: Resource category being acted upon (prompt, backup, etc.).
            resource_id: Identifier of the affected resource.
            status: Operation status (success, failure, warning, etc.).
            event: Optional override for the event field.
            message: Optional human-readable log message.
            **context: Additional metadata fields to include in the log entry.
        """
        audit_logger = self.get_audit_logger()
        payload: Dict[str, Any] = {
            "event": event or f"audit.{resource_type}",
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id),
            "status": status,
        }
        for key, value in context.items():
            if value is not None:
                payload[key] = value

        audit_logger.info(message or f"Audit event: {action}", extra=payload)


logging_service = LoggingService()

__all__ = [
    "logging_service",
    "JsonLogFormatter",
    "ConsoleFormatter",
]
