# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for diff utility functions."""

import pytest
from src.utils.diff_utils import compute_character_diff


class TestComputeCharacterDiff:
    """Test character-level diff computation."""

    def test_character_addition_punctuation(self):
        """Test adding punctuation to the end of a string."""
        result = compute_character_diff("Hello world", "Hello world.")
        assert result == [
            {"op": "equal", "text": "Hello world"},
            {"op": "insert", "text": "."},
        ]

    def test_character_addition_single_char(self):
        """Test adding a single character in the middle."""
        result = compute_character_diff("Hello wrld", "Hello world")
        assert any(d["op"] == "insert" and "o" in d["text"] for d in result)
        assert any(d["op"] == "equal" for d in result)

    def test_character_deletion(self):
        """Test deleting characters from a string."""
        result = compute_character_diff("Hello world!", "Hello world")
        assert result == [
            {"op": "equal", "text": "Hello world"},
            {"op": "delete", "text": "!"},
        ]

    def test_character_deletion_multiple(self):
        """Test deleting multiple characters."""
        result = compute_character_diff("Hello beautiful world", "Hello world")
        assert any(d["op"] == "delete" and "beautiful" in d["text"] for d in result)
        assert any(d["op"] == "equal" for d in result)

    def test_character_replacement(self):
        """Test replacing characters in a string."""
        result = compute_character_diff("Hello world", "Hello Earth")
        # Should have equal part, delete part, and insert part
        ops = [d["op"] for d in result]
        assert "equal" in ops
        assert "delete" in ops or "insert" in ops

    def test_multiline_text(self):
        """Test diff with multiline text."""
        old_text = "Line 1\nLine 2\nLine 3"
        new_text = "Line 1\nLine 2 modified\nLine 3"
        result = compute_character_diff(old_text, new_text)

        # Should have some equal parts and some changes
        ops = [d["op"] for d in result]
        assert "equal" in ops
        assert "insert" in ops or "delete" in ops

    def test_empty_old_string(self):
        """Test when old string is empty (pure addition)."""
        result = compute_character_diff("", "New text")
        assert len(result) == 1
        assert result[0]["op"] == "insert"
        assert result[0]["text"] == "New text"

    def test_empty_new_string(self):
        """Test when new string is empty (pure deletion)."""
        result = compute_character_diff("Old text", "")
        assert len(result) == 1
        assert result[0]["op"] == "delete"
        assert result[0]["text"] == "Old text"

    def test_both_empty_strings(self):
        """Test when both strings are empty."""
        result = compute_character_diff("", "")
        assert result == []

    def test_none_old_string(self):
        """Test when old string is None (treated as empty)."""
        result = compute_character_diff(None, "New text")
        assert len(result) == 1
        assert result[0]["op"] == "insert"
        assert result[0]["text"] == "New text"

    def test_none_new_string(self):
        """Test when new string is None (treated as empty)."""
        result = compute_character_diff("Old text", None)
        assert len(result) == 1
        assert result[0]["op"] == "delete"
        assert result[0]["text"] == "Old text"

    def test_both_none(self):
        """Test when both strings are None."""
        result = compute_character_diff(None, None)
        assert result == []

    def test_identical_strings(self):
        """Test when both strings are identical."""
        text = "Identical text"
        result = compute_character_diff(text, text)
        assert len(result) == 1
        assert result[0]["op"] == "equal"
        assert result[0]["text"] == text

    def test_special_characters(self):
        """Test with special characters and unicode."""
        old_text = "Hello 世界"
        new_text = "Hello 🌍"
        result = compute_character_diff(old_text, new_text)

        # Should have some operations
        assert len(result) > 0
        # Equal part should include "Hello "
        assert any(d["op"] == "equal" and "Hello" in d["text"] for d in result)

    def test_whitespace_changes(self):
        """Test changes in whitespace."""
        old_text = "Hello  world"  # Two spaces
        new_text = "Hello world"  # One space
        result = compute_character_diff(old_text, new_text)

        # Should detect the difference in spacing
        ops = [d["op"] for d in result]
        assert "equal" in ops
        assert "delete" in ops or "insert" in ops

    def test_newline_changes(self):
        """Test changes involving newlines."""
        old_text = "Line 1\nLine 2"
        new_text = "Line 1\n\nLine 2"  # Added extra newline
        result = compute_character_diff(old_text, new_text)

        # Should detect the added newline
        assert any(d["op"] == "insert" and "\n" in d["text"] for d in result)

    def test_long_text_diff(self):
        """Test with longer text blocks."""
        old_text = "This is a longer paragraph with multiple sentences. It contains various words and punctuation marks."
        new_text = "This is a longer paragraph with several sentences. It contains various words and punctuation marks!"
        result = compute_character_diff(old_text, new_text)

        # Should have operations
        assert len(result) > 0
        # Should have equal parts (common text)
        assert any(d["op"] == "equal" for d in result)
        # Should have changes
        assert any(d["op"] in ["insert", "delete"] for d in result)

    def test_complete_text_replacement(self):
        """Test when text is completely replaced."""
        old_text = "ABC"
        new_text = "XYZ"
        result = compute_character_diff(old_text, new_text)

        # Should have delete and insert operations
        ops = [d["op"] for d in result]
        assert "delete" in ops
        assert "insert" in ops

    def test_case_change(self):
        """Test when only case changes."""
        old_text = "hello world"
        new_text = "Hello World"
        result = compute_character_diff(old_text, new_text)

        # Should detect the case changes
        ops = [d["op"] for d in result]
        # Since case is different, there should be changes
        assert "delete" in ops or "insert" in ops

    def test_trailing_whitespace(self):
        """Test with trailing whitespace differences."""
        old_text = "Hello world"
        new_text = "Hello world "  # Added trailing space
        result = compute_character_diff(old_text, new_text)

        assert result == [
            {"op": "equal", "text": "Hello world"},
            {"op": "insert", "text": " "},
        ]

    def test_leading_whitespace(self):
        """Test with leading whitespace differences."""
        old_text = "Hello world"
        new_text = " Hello world"  # Added leading space
        result = compute_character_diff(old_text, new_text)

        assert result[0]["op"] == "insert"
        assert " " in result[0]["text"]

    def test_tab_character(self):
        """Test with tab characters."""
        old_text = "Hello\tworld"
        new_text = "Hello world"  # Replaced tab with space
        result = compute_character_diff(old_text, new_text)

        # Should have some changes
        ops = [d["op"] for d in result]
        assert "equal" in ops
        assert "delete" in ops or "insert" in ops
