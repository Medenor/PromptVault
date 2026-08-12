# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for validation utility functions."""

import os

import pytest

from src.web.validators import (
    create_secure_temp_file,
    get_file_extension_from_format,
    sanitize_backup_name,
    sanitize_filename,
    strip_control_characters,
    validate_file_extension,
    validate_file_size,
)


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_valid_filename(self):
        """Test sanitizing a valid filename."""
        result = sanitize_filename("my_file_123")
        assert result == "my_file_123"

    def test_filename_with_spaces(self):
        """Test that spaces are converted to underscores."""
        result = sanitize_filename("my file name")
        assert result == "my_file_name"

    def test_filename_with_special_characters(self):
        """Test that special characters are removed."""
        result = sanitize_filename("file@#$%^&*()name")
        assert result == "file_name"

    def test_filename_with_extension(self):
        """Test that file extension is removed."""
        result = sanitize_filename("document.pdf")
        assert result == "document"

    def test_path_traversal_attempt(self):
        """Test that path traversal is prevented."""
        result = sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result

    def test_empty_filename_raises_error(self):
        """Test that empty filename raises ValueError."""
        with pytest.raises(ValueError, match="Filename cannot be empty"):
            sanitize_filename("")

    def test_filename_too_long_truncated(self):
        """Test that filename is truncated to max length."""
        long_name = "x" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_consecutive_underscores_removed(self):
        """Test that consecutive underscores are collapsed."""
        result = sanitize_filename("file___name")
        assert result == "file_name"

    def test_leading_trailing_underscores_removed(self):
        """Test that leading/trailing underscores are removed."""
        result = sanitize_filename("___file_name___")
        assert result == "file_name"


class TestSanitizeBackupName:
    """Test backup name sanitization."""

    def test_valid_backup_name(self):
        """Test sanitizing a valid backup name."""
        result = sanitize_backup_name("backup_2024_01_01")
        assert result == "backup_2024_01_01"

    def test_none_backup_name(self):
        """Test that None returns None."""
        result = sanitize_backup_name(None)
        assert result is None

    def test_empty_backup_name(self):
        """Test that empty string returns None."""
        result = sanitize_backup_name("")
        assert result is None

    def test_whitespace_only_backup_name(self):
        """Test that whitespace-only string returns None."""
        result = sanitize_backup_name("   ")
        assert result is None

    def test_backup_name_with_special_characters(self):
        """Test that special characters are replaced."""
        result = sanitize_backup_name("backup@#$123")
        assert result == "backup_123"

    def test_backup_name_too_long_truncated(self):
        """Test that backup name is truncated to 64 characters."""
        long_name = "x" * 100
        result = sanitize_backup_name(long_name)
        assert len(result) <= 64


class TestStripControlCharacters:
    """Test control character stripping."""

    def test_normal_text_unchanged(self):
        """Test that normal text is unchanged."""
        text = "Hello, World!"
        result = strip_control_characters(text)
        assert result == text

    def test_remove_null_byte(self):
        """Test that null byte is removed."""
        text = "Hello\x00World"
        result = strip_control_characters(text)
        assert "\x00" not in result

    def test_preserve_newlines_by_default(self):
        """Test that newlines are preserved by default."""
        text = "Line 1\nLine 2\rLine 3\tTabbed"
        result = strip_control_characters(text)
        assert "\n" in result
        assert "\r" in result
        assert "\t" in result

    def test_remove_newlines_when_disabled(self):
        """Test that newlines are removed when allow_newlines=False."""
        text = "Line 1\nLine 2\rLine 3\tTabbed"
        result = strip_control_characters(text, allow_newlines=False)
        assert "\n" not in result
        assert "\r" not in result
        assert "\t" not in result

    def test_empty_string(self):
        """Test that empty string is handled."""
        result = strip_control_characters("")
        assert result == ""

    def test_bell_character_removed(self):
        """Test that bell character is removed."""
        text = "Alert\x07Message"
        result = strip_control_characters(text)
        assert "\x07" not in result


class TestValidateFileExtension:
    """Test file extension validation."""

    def test_valid_csv_extension(self):
        """Test valid CSV extension."""
        is_valid, ext = validate_file_extension("data.csv")
        assert is_valid is True
        assert ext == ".csv"

    def test_valid_json_extension(self):
        """Test valid JSON extension."""
        is_valid, ext = validate_file_extension("data.json")
        assert is_valid is True
        assert ext == ".json"

    def test_valid_markdown_extension(self):
        """Test valid Markdown extension."""
        is_valid, ext = validate_file_extension("notes.md")
        assert is_valid is True
        assert ext == ".md"

    def test_invalid_extension(self):
        """Test invalid extension."""
        is_valid, ext = validate_file_extension("malware.exe")
        assert is_valid is False
        assert ext == ".exe"

    def test_case_insensitive(self):
        """Test that extension validation is case insensitive."""
        is_valid, ext = validate_file_extension("DATA.CSV")
        assert is_valid is True

    def test_empty_filename(self):
        """Test that empty filename is invalid."""
        is_valid, ext = validate_file_extension("")
        assert is_valid is False


class TestValidateFileSize:
    """Test file size validation."""

    def test_valid_file_size(self):
        """Test valid file size."""
        is_valid, error = validate_file_size(1024)  # 1 KB
        assert is_valid is True
        assert error == ""

    def test_file_size_at_limit(self):
        """Test file size at limit."""
        max_size = 10 * 1024 * 1024  # 10 MB
        is_valid, error = validate_file_size(max_size, max_size)
        assert is_valid is True

    def test_file_size_exceeds_limit(self):
        """Test file size exceeds limit."""
        max_size = 10 * 1024 * 1024  # 10 MB
        is_valid, error = validate_file_size(max_size + 1, max_size)
        assert is_valid is False
        assert "exceeds maximum" in error.lower()

    def test_zero_file_size(self):
        """Test zero file size."""
        is_valid, error = validate_file_size(0)
        assert is_valid is False
        assert "empty" in error.lower()

    def test_negative_file_size(self):
        """Test negative file size."""
        is_valid, error = validate_file_size(-1)
        assert is_valid is False


class TestCreateSecureTempFile:
    """Test secure temporary file creation."""

    def test_create_temp_file(self):
        """Test creating a secure temporary file."""
        temp_path = create_secure_temp_file("test.csv")
        try:
            assert os.path.exists(temp_path)
            assert temp_path.endswith(".csv")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_temp_file_has_random_name(self):
        """Test that temp file has randomized name (not user-provided)."""
        path1 = create_secure_temp_file("test.csv")
        path2 = create_secure_temp_file("test.csv")
        try:
            # Paths should be different (randomized)
            assert path1 != path2
            # But both should have .csv extension
            assert path1.endswith(".csv")
            assert path2.endswith(".csv")
        finally:
            for path in [path1, path2]:
                if os.path.exists(path):
                    os.remove(path)

    def test_path_traversal_prevented(self):
        """Test that path traversal in filename doesn't affect temp file location."""
        temp_path = create_secure_temp_file("../../../etc/passwd.csv")
        try:
            # Path should be in temp directory, not at ../../../etc/
            assert "/etc/passwd" not in temp_path
            assert temp_path.endswith(".csv")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestGetFileExtensionFromFormat:
    """Test getting file extension from format."""

    def test_csv_format(self):
        """Test CSV format."""
        ext = get_file_extension_from_format("csv")
        assert ext == ".csv"

    def test_markdown_format(self):
        """Test Markdown format."""
        ext = get_file_extension_from_format("markdown")
        assert ext == ".md"

    def test_json_format(self):
        """Test JSON format."""
        ext = get_file_extension_from_format("json")
        assert ext == ".json"

    def test_case_insensitive(self):
        """Test that format matching is case insensitive."""
        ext = get_file_extension_from_format("CSV")
        assert ext == ".csv"

    def test_unknown_format(self):
        """Test unknown format returns default."""
        ext = get_file_extension_from_format("unknown")
        assert ext == ".txt"
