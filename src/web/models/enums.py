"""Enumeration types for API validation."""

from enum import Enum


class ExportFormat(str, Enum):
    """Allowed export formats."""

    CSV = "csv"
    MARKDOWN = "markdown"
    JSON = "json"


class ImportMode(str, Enum):
    """Import modes for handling existing data."""

    APPEND = "append"
    MERGE = "merge"
    REPLACE = "replace"
