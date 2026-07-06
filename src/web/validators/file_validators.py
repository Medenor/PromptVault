# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""File upload validation utilities.

This module provides security-focused validation for file uploads including:
- File extension validation
- MIME type validation
- File size limits
- Secure temporary file creation
"""

import os
import tempfile
import mimetypes
from typing import Optional, Tuple
from pathlib import Path
from fastapi import UploadFile

from .constraints import (
    ALLOWED_IMPORT_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
)


def validate_file_extension(
    filename: str, allowed_extensions: set = None
) -> Tuple[bool, str]:
    """Validate that file has an allowed extension.

    Args:
        filename: Name of the file to validate
        allowed_extensions: Set of allowed extensions (default: ALLOWED_IMPORT_EXTENSIONS)

    Returns:
        Tuple of (is_valid: bool, extension: str)

    Example:
        >>> validate_file_extension("data.csv")
        (True, ".csv")
        >>> validate_file_extension("malware.exe")
        (False, ".exe")
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_IMPORT_EXTENSIONS

    if not filename:
        return False, ""

    # Get file extension (lowercase for case-insensitive comparison)
    _, ext = os.path.splitext(filename.lower())

    if ext in allowed_extensions:
        return True, ext
    else:
        return False, ext


def validate_file_size(
    file_size: int, max_size: int = MAX_FILE_SIZE_BYTES
) -> Tuple[bool, str]:
    """Validate that file size is within allowed limits.

    Args:
        file_size: Size of file in bytes
        max_size: Maximum allowed size in bytes

    Returns:
        Tuple of (is_valid: bool, error_message: str)

    Example:
        >>> validate_file_size(1024)
        (True, "")
        >>> validate_file_size(100 * 1024 * 1024)  # 100 MB
        (False, "File size exceeds maximum allowed size of 10 MB")
    """
    if file_size <= 0:
        return False, "File is empty"

    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        actual_size_mb = file_size / (1024 * 1024)
        return (
            False,
            f"File size ({actual_size_mb:.2f} MB) exceeds maximum allowed size of {max_size_mb:.0f} MB",
        )

    return True, ""


def validate_mime_type(content_type: Optional[str], filename: str) -> Tuple[bool, str]:
    """Validate MIME type of uploaded file.

    Checks both the Content-Type header and inferred type from filename extension.

    Args:
        content_type: Content-Type header from upload
        filename: Original filename

    Returns:
        Tuple of (is_valid: bool, detected_type: str)

    Notes:
        Some file types (like .md) may be reported as text/plain by some systems,
        which is acceptable.
    """
    # Infer MIME type from filename extension
    inferred_type, _ = mimetypes.guess_type(filename)

    # Check content type from header if provided
    if content_type:
        # Remove any parameters (e.g., "text/csv; charset=utf-8" -> "text/csv")
        content_type_base = content_type.split(";")[0].strip().lower()

        if content_type_base in ALLOWED_MIME_TYPES:
            return True, content_type_base

    # Check inferred type from filename
    if inferred_type and inferred_type.lower() in ALLOWED_MIME_TYPES:
        return True, inferred_type

    # For markdown files, accept text/plain as valid
    if filename.lower().endswith((".md", ".markdown")):
        return True, "text/markdown"

    return False, inferred_type or content_type or "unknown"


async def validate_upload_file(
    file: UploadFile,
    max_size: int = MAX_FILE_SIZE_BYTES,
    allowed_extensions: set = None,
) -> Tuple[bool, str]:
    """Comprehensive validation of uploaded file.

    Performs all upload validation checks:
    - Extension validation
    - MIME type validation
    - Size validation (by reading file)

    Args:
        file: FastAPI UploadFile object
        max_size: Maximum file size in bytes
        allowed_extensions: Set of allowed extensions

    Returns:
        Tuple of (is_valid: bool, error_message: str)

    Example:
        >>> is_valid, error = await validate_upload_file(uploaded_file)
        >>> if not is_valid:
        ...     return {"error": error}
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_IMPORT_EXTENSIONS

    # Validate filename exists
    if not file.filename:
        return False, "No filename provided"

    # Validate file extension
    ext_valid, ext = validate_file_extension(file.filename, allowed_extensions)
    if not ext_valid:
        allowed_str = ", ".join(sorted(allowed_extensions))
        return (
            False,
            f"Invalid file extension '{ext}'. Allowed extensions: {allowed_str}",
        )

    # Validate MIME type
    mime_valid, mime_type = validate_mime_type(file.content_type, file.filename)
    if not mime_valid:
        allowed_types_str = ", ".join(sorted(ALLOWED_MIME_TYPES))
        return (
            False,
            f"Invalid file type '{mime_type}'. Allowed types: {allowed_types_str}",
        )

    # Validate file size by reading the file
    # Note: This reads the entire file into memory, which is okay for our size limits
    # For larger files, use chunked reading
    content = await file.read()
    file_size = len(content)

    # Reset file position for subsequent reads
    await file.seek(0)

    size_valid, size_error = validate_file_size(file_size, max_size)
    if not size_valid:
        return False, size_error

    return True, ""


def create_secure_temp_file(
    filename: str, suffix: Optional[str] = None, dir: Optional[str] = None
) -> str:
    """Create a secure temporary file for upload processing.

    Uses Python's tempfile module to create a secure temporary file with
    a randomized name to prevent path traversal attacks.

    Args:
        filename: Original filename (used for extension only)
        suffix: Optional suffix for temp file (defaults to file extension)
        dir: Optional directory for temp file (defaults to system temp)

    Returns:
        str: Path to the secure temporary file

    Example:
        >>> temp_path = create_secure_temp_file("upload.csv")
        >>> # Use temp_path for processing
        >>> with open(temp_path, 'wb') as f:
        ...     f.write(content)
        >>> os.remove(temp_path)

    Security:
        - Uses NamedTemporaryFile to generate secure random filenames
        - Prevents path traversal by not using user-supplied filenames
        - Sets appropriate file permissions (0600)
    """
    # Get file extension from original filename
    if suffix is None and filename:
        _, ext = os.path.splitext(filename)
        suffix = ext if ext else ".tmp"

    # Create secure temporary file
    # delete=False because we want to use it after closing
    temp_file = tempfile.NamedTemporaryFile(
        mode="wb", suffix=suffix, dir=dir, delete=False
    )

    temp_path = temp_file.name

    # Close the file but keep the path
    temp_file.close()

    return temp_path


def get_file_extension_from_format(format_str: str) -> str:
    """Get appropriate file extension for export format.

    Args:
        format_str: Export format ("csv", "markdown", "json")

    Returns:
        File extension including dot (e.g., ".csv")
    """
    format_map = {
        "csv": ".csv",
        "markdown": ".md",
        "json": ".json",
    }
    return format_map.get(format_str.lower(), ".txt")


def is_safe_path(base_dir: str, target_path: str) -> bool:
    """Check if target_path is safely within base_dir (no path traversal).

    Args:
        base_dir: The base directory that should contain the target
        target_path: The path to validate

    Returns:
        True if target_path is within base_dir, False otherwise

    Example:
        >>> is_safe_path("/app/data", "/app/data/file.json")
        True
        >>> is_safe_path("/app/data", "/etc/passwd")
        False
        >>> is_safe_path("/app/data", "/app/data/../../../etc/passwd")
        False
    """
    # Resolve to absolute paths
    base = Path(base_dir).resolve()
    target = Path(target_path).resolve()

    # Check if target is relative to base
    try:
        target.relative_to(base)
        return True
    except ValueError:
        # target is not relative to base (path traversal attempt)
        return False
