# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Validation utilities for PromptVault API."""

from .sanitizers import (
    sanitize_filename,
    sanitize_backup_name,
    strip_control_characters,
    sanitize_text_field,
    deduplicate_tags,
    sanitize_tags,
)
from .file_validators import (
    validate_file_extension,
    validate_file_size,
    validate_mime_type,
    validate_upload_file,
    create_secure_temp_file,
    get_file_extension_from_format,
)
from .constraints import (
    MAX_TITLE_LENGTH,
    MAX_PROMPT_LENGTH,
    MAX_CATEGORY_LENGTH,
    MAX_TAG_LENGTH,
    MAX_TAG_COUNT,
    MAX_NOTE_LENGTH,
    MAX_COMMIT_MESSAGE_LENGTH,
    MAX_FILENAME_LENGTH,
    MAX_BACKUP_NAME_LENGTH,
    MAX_FILE_SIZE_BYTES,
    ALLOWED_IMPORT_EXTENSIONS,
    ALLOWED_MIME_TYPES,
)

__all__ = [
    # Sanitizers
    "sanitize_filename",
    "sanitize_backup_name",
    "strip_control_characters",
    "sanitize_text_field",
    "deduplicate_tags",
    "sanitize_tags",
    # File validators
    "validate_file_extension",
    "validate_file_size",
    "validate_mime_type",
    "validate_upload_file",
    "create_secure_temp_file",
    "get_file_extension_from_format",
    # Constraints
    "MAX_TITLE_LENGTH",
    "MAX_PROMPT_LENGTH",
    "MAX_CATEGORY_LENGTH",
    "MAX_TAG_LENGTH",
    "MAX_TAG_COUNT",
    "MAX_NOTE_LENGTH",
    "MAX_COMMIT_MESSAGE_LENGTH",
    "MAX_FILENAME_LENGTH",
    "MAX_BACKUP_NAME_LENGTH",
    "MAX_FILE_SIZE_BYTES",
    "ALLOWED_IMPORT_EXTENSIONS",
    "ALLOWED_MIME_TYPES",
]
