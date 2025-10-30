"""
Comprehensive unit tests for PromptImportExportService.
Tests import/export in CSV and Markdown formats with various edge cases.
"""

import pytest
import os
from pathlib import Path

from src.services.prompt_import_export_service import PromptImportExportService


class TestCSVExport:
    """Test CSV export functionality."""

    def test_export_single_prompt_to_csv(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting a single prompt to CSV."""
        output_file = Path(temp_data_dir) / "export_single.csv"

        prompt_data = sample_prompt_data(
            title="Test Prompt",
            prompt="Test content",
            category="Test",
            tags=["tag1", "tag2"],
        )
        prompts = [(0, {"data": prompt_data})]

        result = import_export_service.export_to_csv(str(output_file), prompts)

        assert result is True
        assert output_file.exists()

        # Verify content
        content = output_file.read_text(encoding="utf-8")
        assert "Test Prompt" in content
        assert "Test content" in content
        assert "tag1, tag2" in content

    def test_export_multiple_prompts_to_csv(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting multiple prompts to CSV."""
        output_file = Path(temp_data_dir) / "export_multiple.csv"

        prompts = [
            (0, {"data": sample_prompt_data(title="Prompt 1")}),
            (1, {"data": sample_prompt_data(title="Prompt 2")}),
            (2, {"data": sample_prompt_data(title="Prompt 3")}),
        ]

        result = import_export_service.export_to_csv(str(output_file), prompts)

        assert result is True

        content = output_file.read_text(encoding="utf-8")
        assert "Prompt 1" in content
        assert "Prompt 2" in content
        assert "Prompt 3" in content

    def test_export_csv_with_special_characters(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting CSV with special characters."""
        output_file = Path(temp_data_dir) / "export_special.csv"

        prompt_data = sample_prompt_data(
            title="Special: <>&\"'",
            prompt='Content with quotes "inside"',
            note="Note with 'single quotes'",
        )
        prompts = [(0, {"data": prompt_data})]

        result = import_export_service.export_to_csv(str(output_file), prompts)

        assert result is True
        assert output_file.exists()

    def test_export_csv_with_commas_in_content(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting CSV with commas in content."""
        output_file = Path(temp_data_dir) / "export_commas.csv"

        prompt_data = sample_prompt_data(
            title="Title, with, commas", prompt="Content, with, multiple, commas"
        )
        prompts = [(0, {"data": prompt_data})]

        result = import_export_service.export_to_csv(str(output_file), prompts)

        assert result is True

    def test_export_csv_with_unicode(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting CSV with Unicode characters."""
        output_file = Path(temp_data_dir) / "export_unicode.csv"

        prompt_data = sample_prompt_data(
            title="Unicode: 你好 ñ é", prompt="Emoji: 🚀 ⭐ 🎉"
        )
        prompts = [(0, {"data": prompt_data})]

        result = import_export_service.export_to_csv(str(output_file), prompts)

        assert result is True

        content = output_file.read_text(encoding="utf-8")
        assert "你好" in content
        assert "🚀" in content

    def test_export_csv_empty_list(self, import_export_service, temp_data_dir):
        """Test exporting empty list to CSV."""
        output_file = Path(temp_data_dir) / "export_empty.csv"

        result = import_export_service.export_to_csv(str(output_file), [])

        assert result is True
        # Should create file with just headers
        content = output_file.read_text(encoding="utf-8")
        assert "title,prompt,note,category,tags,favorite" in content

    def test_export_csv_favorite_conversion(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test that favorite boolean is converted to Yes/No."""
        output_file = Path(temp_data_dir) / "export_favorite.csv"

        prompts = [
            (0, {"data": sample_prompt_data(title="Fav", favorite=True)}),
            (1, {"data": sample_prompt_data(title="NotFav", favorite=False)}),
        ]

        result = import_export_service.export_to_csv(str(output_file), prompts)

        assert result is True

        content = output_file.read_text(encoding="utf-8")
        assert "Yes" in content
        assert "No" in content


class TestCSVImport:
    """Test CSV import functionality."""

    def test_import_valid_csv(
        self, import_export_service, temp_data_dir, sample_csv_content
    ):
        """Test importing a valid CSV file."""
        csv_file = Path(temp_data_dir) / "import.csv"
        csv_file.write_text(sample_csv_content, encoding="utf-8")

        prompts = import_export_service.import_from_csv(str(csv_file))

        assert len(prompts) == 2
        assert prompts[0]["title"] == "Test Prompt 1"
        assert prompts[0]["category"] == "Category1"
        assert prompts[0]["favorite"] is True
        assert "tag1" in prompts[0]["tags"]

    def test_import_csv_with_missing_optional_fields(
        self, import_export_service, temp_data_dir
    ):
        """Test importing CSV with missing optional fields."""
        csv_content = """title,prompt,note,category,tags,favorite
Basic Title,Basic Content,,,
"""
        csv_file = Path(temp_data_dir) / "import_minimal.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        prompts = import_export_service.import_from_csv(str(csv_file))

        assert len(prompts) == 1
        assert prompts[0]["title"] == "Basic Title"
        assert prompts[0]["category"] == "No category"
        assert prompts[0]["tags"] == []
        assert prompts[0]["favorite"] is False

    def test_import_csv_favorite_yes_no_conversion(
        self, import_export_service, temp_data_dir
    ):
        """Test converting Yes/No to boolean for favorite field."""
        csv_content = """title,prompt,note,category,tags,favorite
Fav1,Content,,Category,,Yes
Fav2,Content,,Category,,yes
Fav3,Content,,Category,,YES
NotFav,Content,,Category,,No
"""
        csv_file = Path(temp_data_dir) / "import_favorite.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        prompts = import_export_service.import_from_csv(str(csv_file))

        assert len(prompts) == 4
        assert prompts[0]["favorite"] is True
        assert prompts[1]["favorite"] is True
        assert prompts[2]["favorite"] is True
        assert prompts[3]["favorite"] is False

    def test_import_csv_tags_parsing(self, import_export_service, temp_data_dir):
        """Test parsing comma-separated tags."""
        csv_content = """title,prompt,note,category,tags,favorite
Test,Content,,Category,"tag1, tag2, tag3",No
"""
        csv_file = Path(temp_data_dir) / "import_tags.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        prompts = import_export_service.import_from_csv(str(csv_file))

        assert len(prompts[0]["tags"]) == 3
        assert "tag1" in prompts[0]["tags"]
        assert "tag2" in prompts[0]["tags"]
        assert "tag3" in prompts[0]["tags"]

    def test_import_csv_empty_tags(self, import_export_service, temp_data_dir):
        """Test importing CSV with empty tags field."""
        csv_content = """title,prompt,note,category,tags,favorite
Test,Content,,Category,,No
"""
        csv_file = Path(temp_data_dir) / "import_no_tags.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        prompts = import_export_service.import_from_csv(str(csv_file))

        assert prompts[0]["tags"] == []

    def test_import_csv_with_special_characters(
        self, import_export_service, temp_data_dir
    ):
        """Test importing CSV with special characters."""
        csv_content = '''title,prompt,note,category,tags,favorite
"Special: <>","Content with ""quotes""",Note,Category,tag,No
'''
        csv_file = Path(temp_data_dir) / "import_special.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        prompts = import_export_service.import_from_csv(str(csv_file))

        assert len(prompts) == 1
        assert "Special" in prompts[0]["title"]

    def test_import_nonexistent_csv(self, import_export_service, temp_data_dir):
        """Test importing a file that doesn't exist."""
        prompts = import_export_service.import_from_csv(
            str(Path(temp_data_dir) / "nonexistent.csv")
        )

        # Should return empty list, not crash
        assert prompts == []

    def test_import_empty_csv(self, import_export_service, temp_data_dir):
        """Test importing an empty CSV file."""
        csv_file = Path(temp_data_dir) / "empty.csv"
        csv_file.write_text("", encoding="utf-8")

        prompts = import_export_service.import_from_csv(str(csv_file))

        assert prompts == []


class TestMarkdownExport:
    """Test Markdown export functionality."""

    def test_export_single_prompt_to_markdown(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting a single prompt to Markdown."""
        output_file = Path(temp_data_dir) / "export.md"

        prompt_data = sample_prompt_data(
            title="Test Prompt",
            prompt="Test content",
            note="Test note",
            category="Test",
            tags=["tag1", "tag2"],
        )
        prompts = [(0, {"data": prompt_data})]

        result = import_export_service.export_to_markdown(str(output_file), prompts)

        assert result is True
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert "# Test Prompt" in content
        assert "**Category:** Test" in content
        assert "**Tags:** tag1, tag2" in content
        assert "## Prompt" in content
        assert "Test content" in content
        assert "## Note" in content
        assert "Test note" in content

    def test_export_multiple_prompts_to_markdown(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting multiple prompts to Markdown."""
        output_file = Path(temp_data_dir) / "export_multiple.md"

        prompts = [
            (0, {"data": sample_prompt_data(title="Prompt 1")}),
            (1, {"data": sample_prompt_data(title="Prompt 2")}),
        ]

        result = import_export_service.export_to_markdown(str(output_file), prompts)

        assert result is True

        content = output_file.read_text(encoding="utf-8")
        assert "# Prompt 1" in content
        assert "# Prompt 2" in content
        assert content.count("---") == 2  # Separator between prompts

    def test_export_markdown_with_formatting(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting Markdown with formatting characters."""
        output_file = Path(temp_data_dir) / "export_format.md"

        prompt_data = sample_prompt_data(
            title="**Bold** Title", prompt="Content with *italic* and **bold**"
        )
        prompts = [(0, {"data": prompt_data})]

        result = import_export_service.export_to_markdown(str(output_file), prompts)

        assert result is True

    def test_export_markdown_with_unicode(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting Markdown with Unicode."""
        output_file = Path(temp_data_dir) / "export_unicode.md"

        prompt_data = sample_prompt_data(title="Unicode: 你好", prompt="Emoji: 🚀")
        prompts = [(0, {"data": prompt_data})]

        result = import_export_service.export_to_markdown(str(output_file), prompts)

        assert result is True

        content = output_file.read_text(encoding="utf-8")
        assert "你好" in content
        assert "🚀" in content

    def test_export_markdown_empty_list(self, import_export_service, temp_data_dir):
        """Test exporting empty list to Markdown."""
        output_file = Path(temp_data_dir) / "export_empty.md"

        result = import_export_service.export_to_markdown(str(output_file), [])

        assert result is True
        # Should create empty file or file with no content
        assert output_file.exists()

    def test_export_markdown_without_note(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting Markdown without note field."""
        output_file = Path(temp_data_dir) / "export_no_note.md"

        prompt_data = sample_prompt_data(note="")
        prompts = [(0, {"data": prompt_data})]

        result = import_export_service.export_to_markdown(str(output_file), prompts)

        assert result is True

        content = output_file.read_text(encoding="utf-8")
        # Note section should not appear if empty
        assert content.count("## Note") == 0

    def test_export_markdown_favorite_conversion(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test that favorite boolean is converted to Yes/No in Markdown."""
        output_file = Path(temp_data_dir) / "export_favorite.md"

        prompts = [
            (0, {"data": sample_prompt_data(title="Fav", favorite=True)}),
            (1, {"data": sample_prompt_data(title="NotFav", favorite=False)}),
        ]

        result = import_export_service.export_to_markdown(str(output_file), prompts)

        assert result is True

        content = output_file.read_text(encoding="utf-8")
        assert "**Favorite:** Yes" in content
        assert "**Favorite:** No" in content


class TestMarkdownImport:
    """Test Markdown import functionality."""

    def test_import_valid_markdown(
        self, import_export_service, temp_data_dir, sample_markdown_content
    ):
        """Test importing a valid Markdown file."""
        md_file = Path(temp_data_dir) / "import.md"
        md_file.write_text(sample_markdown_content, encoding="utf-8")

        prompts = import_export_service.import_from_markdown(str(md_file))

        assert len(prompts) == 2
        assert prompts[0]["title"] == "Test Prompt 1"
        assert prompts[0]["category"] == "Category1"
        assert prompts[0]["favorite"] is True
        assert "tag1" in prompts[0]["tags"]

    def test_import_markdown_with_missing_sections(
        self, import_export_service, temp_data_dir
    ):
        """Test importing Markdown with missing optional sections."""
        md_content = """# Minimal Prompt

## Prompt
Basic content

---
"""
        md_file = Path(temp_data_dir) / "import_minimal.md"
        md_file.write_text(md_content, encoding="utf-8")

        prompts = import_export_service.import_from_markdown(str(md_file))

        assert len(prompts) == 1
        assert prompts[0]["title"] == "Minimal Prompt"
        assert prompts[0]["prompt"].strip() == "Basic content"

    def test_import_markdown_favorite_conversion(
        self, import_export_service, temp_data_dir
    ):
        """Test converting Yes/No to boolean for favorite field."""
        md_content = """# Fav Prompt

**Favorite:** Yes

## Prompt
Content

---

# Not Fav Prompt

**Favorite:** No

## Prompt
Content

---
"""
        md_file = Path(temp_data_dir) / "import_favorite.md"
        md_file.write_text(md_content, encoding="utf-8")

        prompts = import_export_service.import_from_markdown(str(md_file))

        assert len(prompts) == 2
        assert prompts[0]["favorite"] is True
        assert prompts[1]["favorite"] is False

    def test_import_markdown_tags_parsing(self, import_export_service, temp_data_dir):
        """Test parsing comma-separated tags from Markdown."""
        md_content = """# Test Prompt

**Tags:** tag1, tag2, tag3

## Prompt
Content

---
"""
        md_file = Path(temp_data_dir) / "import_tags.md"
        md_file.write_text(md_content, encoding="utf-8")

        prompts = import_export_service.import_from_markdown(str(md_file))

        assert len(prompts[0]["tags"]) == 3
        assert "tag1" in prompts[0]["tags"]
        assert "tag2" in prompts[0]["tags"]
        assert "tag3" in prompts[0]["tags"]

    def test_import_markdown_multiline_content(
        self, import_export_service, temp_data_dir
    ):
        """Test importing Markdown with multiline prompt content."""
        md_content = """# Test

## Prompt
Line 1
Line 2
Line 3

## Note
Note line 1
Note line 2

---
"""
        md_file = Path(temp_data_dir) / "import_multiline.md"
        md_file.write_text(md_content, encoding="utf-8")

        prompts = import_export_service.import_from_markdown(str(md_file))

        assert len(prompts) == 1
        assert "Line 1" in prompts[0]["prompt"]
        assert "Line 2" in prompts[0]["prompt"]
        assert "Note line 1" in prompts[0]["note"]

    def test_import_markdown_with_special_characters(
        self, import_export_service, temp_data_dir
    ):
        """Test importing Markdown with special characters."""
        md_content = """# Special: <>&

## Prompt
Content with "quotes" and 'apostrophes'

---
"""
        md_file = Path(temp_data_dir) / "import_special.md"
        md_file.write_text(md_content, encoding="utf-8")

        prompts = import_export_service.import_from_markdown(str(md_file))

        assert len(prompts) == 1
        assert "Special" in prompts[0]["title"]

    def test_import_nonexistent_markdown(self, import_export_service, temp_data_dir):
        """Test importing a file that doesn't exist."""
        prompts = import_export_service.import_from_markdown(
            str(Path(temp_data_dir) / "nonexistent.md")
        )

        # Should return empty list, not crash
        assert prompts == []

    def test_import_empty_markdown(self, import_export_service, temp_data_dir):
        """Test importing an empty Markdown file."""
        md_file = Path(temp_data_dir) / "empty.md"
        md_file.write_text("", encoding="utf-8")

        prompts = import_export_service.import_from_markdown(str(md_file))

        assert prompts == []

    def test_import_markdown_malformed_structure(
        self, import_export_service, temp_data_dir
    ):
        """Test importing Markdown with malformed structure."""
        md_content = """Random text without proper structure
No headers or sections
Just plain text
"""
        md_file = Path(temp_data_dir) / "import_malformed.md"
        md_file.write_text(md_content, encoding="utf-8")

        prompts = import_export_service.import_from_markdown(str(md_file))

        # Should handle gracefully, possibly returning empty or partial data
        assert isinstance(prompts, list)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_export_csv_invalid_path(self, import_export_service):
        """Test exporting to an invalid path."""
        result = import_export_service.export_to_csv("/invalid/path/file.csv", [])

        # Should fail gracefully
        assert result is False

    def test_export_markdown_invalid_path(self, import_export_service):
        """Test exporting Markdown to an invalid path."""
        result = import_export_service.export_to_markdown("/invalid/path/file.md", [])

        # Should fail gracefully
        assert result is False

    def test_import_csv_malformed_rows(self, import_export_service, temp_data_dir):
        """Test importing CSV with malformed rows."""
        csv_content = """title,prompt,note,category,tags,favorite
Complete Row,Content,Note,Cat,tags,Yes
Incomplete Row
Another Complete,Content2,Note2,Cat2,tags2,No
"""
        csv_file = Path(temp_data_dir) / "malformed.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        prompts = import_export_service.import_from_csv(str(csv_file))

        # Should import valid rows, skip malformed ones
        assert len(prompts) >= 2

    def test_round_trip_csv(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting and then importing CSV maintains data."""
        export_file = Path(temp_data_dir) / "roundtrip.csv"

        original_prompt = sample_prompt_data(
            title="Round Trip Test",
            prompt="Test content",
            category="TestCat",
            tags=["tag1", "tag2"],
        )
        prompts = [(0, {"data": original_prompt})]

        # Export
        import_export_service.export_to_csv(str(export_file), prompts)

        # Import
        imported = import_export_service.import_from_csv(str(export_file))

        assert len(imported) == 1
        assert imported[0]["title"] == original_prompt["title"]
        assert imported[0]["prompt"] == original_prompt["prompt"]
        assert imported[0]["category"] == original_prompt["category"]

    def test_round_trip_markdown(
        self, import_export_service, temp_data_dir, sample_prompt_data
    ):
        """Test exporting and then importing Markdown maintains data."""
        export_file = Path(temp_data_dir) / "roundtrip.md"

        original_prompt = sample_prompt_data(
            title="Round Trip Test",
            prompt="Test content",
            note="Test note",
            category="TestCat",
            tags=["tag1", "tag2"],
        )
        prompts = [(0, {"data": original_prompt})]

        # Export
        import_export_service.export_to_markdown(str(export_file), prompts)

        # Import
        imported = import_export_service.import_from_markdown(str(export_file))

        assert len(imported) == 1
        assert imported[0]["title"] == original_prompt["title"]
        assert imported[0]["category"] == original_prompt["category"]
