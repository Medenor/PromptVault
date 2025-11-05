"""Shared validation constraints for PromptVault.

This module defines all validation constraints in one place for consistency
across Pydantic models, service layer, and client-side validation.
"""

# Text field length constraints
MAX_TITLE_LENGTH = 200
MAX_PROMPT_LENGTH = 50000
MAX_CATEGORY_LENGTH = 100
MAX_TAG_LENGTH = 50
MAX_TAG_COUNT = 50
MAX_NOTE_LENGTH = 10000
MAX_COMMIT_MESSAGE_LENGTH = 500

# Filename constraints
MAX_FILENAME_LENGTH = 255
MAX_BACKUP_NAME_LENGTH = 64

# File upload constraints
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_FILE_SIZE_MB = 10

# Allowed file extensions for import
ALLOWED_IMPORT_EXTENSIONS = {".csv", ".json", ".md", ".markdown"}

# Allowed MIME types for import
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/json",
    "text/markdown",
    "text/plain",  # Some systems report .md as text/plain
}

# Backup retention constraints
MIN_RETENTION_DAYS = 1
MAX_RETENTION_DAYS = 3650  # 10 years

MIN_COMPRESSION_THRESHOLD_DAYS = 1
MAX_COMPRESSION_THRESHOLD_DAYS = 365  # 1 year

# Regular expressions for validation
SAFE_FILENAME_PATTERN = r"^[A-Za-z0-9_-]+$"
SAFE_BACKUP_NAME_PATTERN = r"^[A-Za-z0-9_-]+$"

# Character sets
CONTROL_CHARACTERS = "".join(
    chr(i) for i in range(32) if chr(i) not in "\n\r\t"
)  # Exclude newline, carriage return, tab
