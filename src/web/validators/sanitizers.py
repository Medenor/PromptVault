# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Sanitization utilities for user input.

This module provides functions to sanitize and clean user input
to prevent security vulnerabilities and ensure data integrity.
"""

import re
import os
from typing import Optional
from .constraints import (
    SAFE_FILENAME_PATTERN,
    SAFE_BACKUP_NAME_PATTERN,
    MAX_FILENAME_LENGTH,
    MAX_BACKUP_NAME_LENGTH,
    CONTROL_CHARACTERS,
)


def sanitize_filename(filename: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """Sanitize a filename to prevent path traversal and ensure filesystem safety.

    Args:
        filename: The filename to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized filename safe for filesystem operations

    Raises:
        ValueError: If filename is empty or contains only invalid characters
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Extract basename to remove any path components (path traversal protection)
    filename = os.path.basename(filename)

    # Remove file extension if present (will be added based on format)
    name_without_ext = os.path.splitext(filename)[0]

    if not name_without_ext:
        raise ValueError("Filename cannot be empty after removing extension")

    # Replace any characters not in the safe set with underscore
    sanitized = re.sub(r"[^A-Za-z0-9_-]", "_", name_without_ext)

    # Remove consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    if not sanitized:
        raise ValueError("Filename contains only invalid characters")

    # Truncate to max length
    sanitized = sanitized[:max_length]

    return sanitized


def sanitize_backup_name(name: Optional[str]) -> Optional[str]:
    """Sanitize a backup name for safe filesystem storage.

    Args:
        name: The backup name to sanitize (can be None)

    Returns:
        Sanitized backup name or None if input is None/empty

    Raises:
        ValueError: If name contains only invalid characters after sanitization
    """
    if name is None or name == "":
        return None

    name = name.strip()
    if not name:
        return None

    # Replace any characters not in the safe set with underscore
    sanitized = re.sub(r"[^A-Za-z0-9_-]", "_", name)

    # Remove consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    if not sanitized:
        raise ValueError("Backup name contains only invalid characters")

    # Truncate to max length
    sanitized = sanitized[:MAX_BACKUP_NAME_LENGTH]

    return sanitized


def strip_control_characters(text: str, allow_newlines: bool = True) -> str:
    """Remove control characters from text while preserving printable characters.

    Args:
        text: Input text to clean
        allow_newlines: If True, preserve newline, carriage return, and tab characters

    Returns:
        Text with control characters removed

    Notes:
        This helps prevent log injection and display issues with unusual characters.
        By default, preserves \\n, \\r, \\t for legitimate text formatting.
    """
    if not text:
        return text

    if allow_newlines:
        # Remove control characters except newline, carriage return, tab
        return "".join(char for char in text if char not in CONTROL_CHARACTERS)
    else:
        # Remove all control characters (ASCII 0-31 and 127)
        return "".join(char for char in text if ord(char) >= 32 and ord(char) != 127)


def validate_path_safety(path: str) -> bool:
    """Check if a path is safe (no traversal attempts).

    Args:
        path: Path to validate

    Returns:
        True if path is safe, False otherwise

    Examples:
        >>> validate_path_safety("file.json")
        True
        >>> validate_path_safety("../etc/passwd")
        False
        >>> validate_path_safety("/absolute/path")
        False
    """
    if not path:
        return False

    # Check for path traversal patterns
    if ".." in path:
        return False

    # Check for path separators (should be basename only)
    if "/" in path or "\\" in path:
        return False

    # Check for absolute path indicators
    if path.startswith(("/", "\\")):
        return False

    return True


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text.

    - Strips leading/trailing whitespace
    - Replaces multiple consecutive spaces with single space
    - Preserves newlines

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    if not text:
        return text

    # Split into lines to preserve newlines
    lines = text.split("\n")

    # Normalize each line
    normalized_lines = []
    for line in lines:
        # Replace multiple spaces with single space
        normalized = re.sub(r" +", " ", line)
        # Strip leading/trailing whitespace from line
        normalized = normalized.strip()
        normalized_lines.append(normalized)

    # Rejoin with newlines
    return "\n".join(normalized_lines)


def sanitize_text_field(text: str, max_length: Optional[int] = None, allow_newlines: bool = True) -> str:
    """Comprehensive sanitization for text fields.

    Applies multiple sanitization steps:
    1. Strip control characters
    2. Normalize whitespace
    3. Trim to max length if specified

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (optional)
        allow_newlines: Whether to preserve newlines

    Returns:
        Sanitized text

    Examples:
        >>> sanitize_text_field("Hello\\x00World")
        'Hello World'
        >>> sanitize_text_field("  Too   many   spaces  ")
        'Too many spaces'
    """
    if not text:
        return text

    # Step 1: Remove control characters
    text = strip_control_characters(text, allow_newlines=allow_newlines)

    # Step 2: Normalize whitespace
    if not allow_newlines:
        # If newlines not allowed, treat as single line
        text = " ".join(text.split())
    else:
        text = normalize_whitespace(text)

    # Step 3: Trim to max length if specified
    if max_length and len(text) > max_length:
        text = text[:max_length]

    return text.strip()


def deduplicate_tags(tags: list) -> list:
    """Remove duplicate tags while preserving order.

    Args:
        tags: List of tags (may contain duplicates)

    Returns:
        List of unique tags in original order

    Examples:
        >>> deduplicate_tags(['python', 'coding', 'python', 'ai'])
        ['python', 'coding', 'ai']
        >>> deduplicate_tags(['a', 'b', 'a', 'c', 'b'])
        ['a', 'b', 'c']
    """
    if not tags:
        return []

    seen = set()
    unique_tags = []

    for tag in tags:
        # Normalize: strip whitespace and convert to lowercase for comparison
        normalized = tag.strip().lower() if isinstance(tag, str) else str(tag).strip().lower()

        if normalized and normalized not in seen:
            seen.add(normalized)
            # Keep original case for the first occurrence
            unique_tags.append(tag.strip() if isinstance(tag, str) else str(tag).strip())

    return unique_tags


def sanitize_tags(tags: list, max_count: int = 50, max_length_per_tag: int = 50) -> list:
    """Sanitize a list of tags.

    Applies:
    1. Tag deduplication
    2. Control character removal
    3. Whitespace normalization
    4. Length limits per tag
    5. Maximum tag count

    Args:
        tags: List of tags to sanitize
        max_count: Maximum number of tags allowed
        max_length_per_tag: Maximum length per individual tag

    Returns:
        List of sanitized, unique tags

    Examples:
        >>> sanitize_tags(['python', 'PYTHON', 'coding'])
        ['python', 'coding']
        >>> sanitize_tags(['a'] * 60, max_count=50)  # Returns first 50 unique
        ['a']
    """
    if not tags:
        return []

    # Deduplicate first
    unique_tags = deduplicate_tags(tags)

    # Sanitize each tag
    sanitized = []
    for tag in unique_tags[:max_count]:  # Limit to max_count
        if isinstance(tag, str):
            # Remove control characters and normalize
            clean_tag = sanitize_text_field(tag, max_length=max_length_per_tag, allow_newlines=False)
            if clean_tag:  # Only add non-empty tags
                sanitized.append(clean_tag)

    return sanitized
