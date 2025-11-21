"""
Custom exception hierarchy for PromptVault services.
"""
from typing import Any, Dict, Optional


class PromptVaultException(Exception):
    """
    Base exception for all service-layer failures.

    Attributes:
        message: Developer-focused error string.
        user_message: Safe message for API consumers.
        http_status: HTTP status code associated with the error.
        log_level: Logging severity to use when reporting the error.
        context: Structured metadata describing the failure (ids, file paths, etc.).
    """

    def __init__(
        self,
        message: str,
        *,
        user_message: Optional[str] = None,
        http_status: int = 500,
        log_level: str = "error",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.user_message = user_message or "An unexpected error occurred."
        self.http_status = http_status
        self.log_level = log_level
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation for API responses."""
        return {
            "error": self.user_message,
            "details": self.context,
        }


class DataPersistenceError(PromptVaultException):
    """Raised when prompt data cannot be saved or loaded."""

    def __init__(
        self,
        message: str,
        *,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message,
            user_message=user_message or "Unable to persist prompt data.",
            http_status=500,
            log_level="error",
            context=context,
        )


class BackupError(PromptVaultException):
    """Raised for backup/restore failures."""

    def __init__(
        self,
        message: str,
        *,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        http_status: int = 500,
    ) -> None:
        super().__init__(
            message,
            user_message=user_message or "Backup operation failed.",
            http_status=http_status,
            log_level="error",
            context=context,
        )


class ImportExportError(PromptVaultException):
    """Raised when import/export operations fail."""

    def __init__(
        self,
        message: str,
        *,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message,
            user_message=user_message
            or "Import/export operation could not be completed.",
            http_status=400,
            log_level="warning",
            context=context,
        )


class ValidationMonitorError(PromptVaultException):
    """Raised when validation monitoring cannot persist metrics."""

    def __init__(
        self,
        message: str,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Validation metrics could not be recorded.",
            http_status=500,
            log_level="warning",
            context=context,
        )
