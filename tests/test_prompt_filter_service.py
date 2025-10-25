"""
Comprehensive unit tests for PromptFilterService.
Tests filtering by category, tag, search term, favorites, and sorting.
"""

import pytest
from src.services.prompt_filter_service import PromptFilterService


class TestFilterByCategory:
    """Test filtering prompts by category."""

    def test_filter_by_single_category(self, filter_service, populated_data_service):
        """Test filtering by a single category."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, filter_category="Programming")

        assert len(filtered) >= 1
        for prompt in filtered:
            assert prompt['category'] == "Programming"

    def test_filter_by_nonexistent_category(self, filter_service, populated_data_service):
        """Test filtering by a category that doesn't exist."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, filter_category="Nonexistent")

        assert len(filtered) == 0

    def test_filter_no_category_returns_all(self, filter_service, populated_data_service):
        """Test that no category filter returns all prompts."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, filter_category=None)

        assert len(filtered) == len(prompts)


class TestFilterByTag:
    """Test filtering prompts by tag."""

    def test_filter_by_single_tag(self, filter_service, populated_data_service):
        """Test filtering by a single tag."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, filter_tag="python")

        assert len(filtered) >= 1
        for prompt in filtered:
            assert "python" in prompt['tags']

    def test_filter_by_nonexistent_tag(self, filter_service, populated_data_service):
        """Test filtering by a tag that doesn't exist."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, filter_tag="nonexistent_tag")

        assert len(filtered) == 0

    def test_filter_no_tag_returns_all(self, filter_service, populated_data_service):
        """Test that no tag filter returns all prompts."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, filter_tag=None)

        assert len(filtered) == len(prompts)

    def test_filter_prompt_with_multiple_tags(self, filter_service, populated_data_service):
        """Test filtering finds prompts with multiple tags."""
        prompts = populated_data_service.prompts
        # Filter by a tag that appears in prompts with other tags
        filtered = filter_service.filter_prompts(prompts, filter_tag="coding")

        assert len(filtered) >= 1


class TestSearchTerm:
    """Test search term filtering."""

    def test_search_in_title(self, filter_service, populated_data_service):
        """Test searching for text in title."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, search_term="Python")

        assert len(filtered) >= 1
        for prompt in filtered:
            assert "Python" in prompt['title'] or "Python" in prompt['prompt'] or "Python" in prompt.get('note', '')

    def test_search_in_prompt_content(self, filter_service, populated_data_service):
        """Test searching for text in prompt content."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, search_term="code")

        assert len(filtered) >= 1

    def test_search_in_note(self, filter_service, empty_data_service, sample_prompt_data):
        """Test searching for text in note field."""
        prompt_data = sample_prompt_data(
            title="Test",
            prompt="Content",
            note="Special note with unique keyword"
        )
        empty_data_service.add_new_prompt(prompt_data)

        prompts = empty_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, search_term="unique")

        assert len(filtered) == 1

    def test_search_empty_string_returns_all(self, filter_service, populated_data_service):
        """Test that empty search term returns all prompts."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, search_term="")

        assert len(filtered) == len(prompts)

    def test_search_case_insensitive(self, filter_service, populated_data_service):
        """Test case-insensitive search."""
        prompts = populated_data_service.prompts
        filtered_lower = filter_service.filter_prompts(prompts, search_term="python", case_sensitive=False)
        filtered_upper = filter_service.filter_prompts(prompts, search_term="PYTHON", case_sensitive=False)

        assert len(filtered_lower) == len(filtered_upper)
        assert len(filtered_lower) >= 1

    def test_search_case_sensitive(self, filter_service, empty_data_service, sample_prompt_data):
        """Test case-sensitive search."""
        empty_data_service.add_new_prompt(sample_prompt_data(title="Python"))
        empty_data_service.add_new_prompt(sample_prompt_data(title="python"))

        prompts = empty_data_service.prompts

        filtered_upper = filter_service.filter_prompts(prompts, search_term="Python", case_sensitive=True)
        filtered_lower = filter_service.filter_prompts(prompts, search_term="python", case_sensitive=True)

        # With case-sensitive, should match exact case
        assert len(filtered_upper) >= 1
        assert len(filtered_lower) >= 1

    def test_search_with_special_characters(self, filter_service, empty_data_service, sample_prompt_data):
        """Test searching with special characters."""
        prompt_data = sample_prompt_data(title="Test: Special <>&")
        empty_data_service.add_new_prompt(prompt_data)

        prompts = empty_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, search_term="<>&")

        assert len(filtered) == 1

    def test_search_with_unicode(self, filter_service, empty_data_service, sample_prompt_data):
        """Test searching with Unicode characters."""
        prompt_data = sample_prompt_data(title="Unicode 你好")
        empty_data_service.add_new_prompt(prompt_data)

        prompts = empty_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, search_term="你好")

        assert len(filtered) == 1

    def test_search_no_match(self, filter_service, populated_data_service):
        """Test search with no matches."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, search_term="xyznonexistent123")

        assert len(filtered) == 0


class TestFilterByFavorites:
    """Test filtering by favorite status."""

    def test_filter_favorites_only(self, filter_service, populated_data_service):
        """Test filtering to show only favorites."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, filter_favorites=True)

        assert len(filtered) >= 1
        for prompt in filtered:
            assert prompt['favorite'] is True

    def test_filter_favorites_false_shows_all(self, filter_service, populated_data_service):
        """Test that favorites=False shows all prompts."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, filter_favorites=False)

        assert len(filtered) == len(prompts)

    def test_filter_favorites_with_no_favorites(self, filter_service, empty_data_service, sample_prompt_data):
        """Test filtering favorites when none exist."""
        empty_data_service.add_new_prompt(sample_prompt_data(favorite=False))
        empty_data_service.add_new_prompt(sample_prompt_data(favorite=False))

        prompts = empty_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, filter_favorites=True)

        assert len(filtered) == 0


class TestCombinedFilters:
    """Test combinations of multiple filters."""

    def test_filter_category_and_tag(self, filter_service, populated_data_service):
        """Test filtering by both category and tag."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(
            prompts,
            filter_category="Development",
            filter_tag="review"
        )

        for prompt in filtered:
            assert prompt['category'] == "Development"
            assert "review" in prompt['tags']

    def test_filter_category_and_search(self, filter_service, populated_data_service):
        """Test filtering by category and search term."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(
            prompts,
            filter_category="Programming",
            search_term="Python"
        )

        for prompt in filtered:
            assert prompt['category'] == "Programming"

    def test_filter_tag_and_search(self, filter_service, populated_data_service):
        """Test filtering by tag and search term."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(
            prompts,
            filter_tag="security",
            search_term="audit"
        )

        for prompt in filtered:
            assert "security" in prompt['tags']

    def test_filter_favorites_and_category(self, filter_service, populated_data_service):
        """Test filtering by favorites and category."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(
            prompts,
            filter_favorites=True,
            filter_category="Security"
        )

        for prompt in filtered:
            assert prompt['favorite'] is True
            assert prompt['category'] == "Security"

    def test_filter_all_criteria(self, filter_service, empty_data_service, sample_prompt_data):
        """Test filtering with all criteria combined."""
        # Add a prompt that matches all criteria
        prompt_data = sample_prompt_data(
            title="Special Python Test",
            prompt="Python code",
            category="TestCategory",
            tags=["testtag"],
            favorite=True
        )
        empty_data_service.add_new_prompt(prompt_data)

        # Add prompts that don't match
        empty_data_service.add_new_prompt(sample_prompt_data(category="Other"))
        empty_data_service.add_new_prompt(sample_prompt_data(tags=["other"]))

        prompts = empty_data_service.prompts
        filtered = filter_service.filter_prompts(
            prompts,
            filter_category="TestCategory",
            filter_tag="testtag",
            search_term="Python",
            filter_favorites=True
        )

        assert len(filtered) == 1
        assert filtered[0]['title'] == "Special Python Test"


class TestSorting:
    """Test prompt sorting functionality."""

    def test_sort_by_title(self, filter_service, populated_data_service):
        """Test sorting prompts by title."""
        prompts = populated_data_service.prompts
        filtered = filter_service.filter_prompts(prompts)
        sorted_prompts = filter_service.sort_prompts(filtered)

        titles = [p['title'] for p in sorted_prompts]
        assert titles == sorted(titles)

    def test_sort_empty_list(self, filter_service):
        """Test sorting an empty list."""
        sorted_prompts = filter_service.sort_prompts([])

        assert sorted_prompts == []

    def test_sort_single_prompt(self, filter_service):
        """Test sorting a single prompt."""
        prompts = [{'title': 'Single', 'prompt': 'Content'}]
        sorted_prompts = filter_service.sort_prompts(prompts)

        assert len(sorted_prompts) == 1
        assert sorted_prompts[0]['title'] == 'Single'

    def test_sort_with_missing_titles(self, filter_service):
        """Test sorting with some prompts missing titles."""
        prompts = [
            {'title': 'B', 'prompt': 'Content'},
            {'prompt': 'No title'},
            {'title': 'A', 'prompt': 'Content'}
        ]
        sorted_prompts = filter_service.sort_prompts(prompts)

        # Prompts with missing titles should have empty string and sort first
        assert sorted_prompts[0].get('title', '') == ''
        assert sorted_prompts[1]['title'] == 'A'
        assert sorted_prompts[2]['title'] == 'B'


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_filter_empty_prompts_dict(self, filter_service):
        """Test filtering an empty prompts dictionary."""
        filtered = filter_service.filter_prompts({})

        assert filtered == []

    def test_filter_prompts_with_missing_fields(self, filter_service):
        """Test filtering prompts with missing fields."""
        prompts = {
            0: {'data': {'title': 'Test'}},  # Missing prompt, category, tags
            1: {'data': {'prompt': 'Content'}},  # Missing title
        }

        filtered = filter_service.filter_prompts(prompts)

        # Should handle gracefully without crashing
        assert len(filtered) == 2

    def test_filter_prompts_with_none_values(self, filter_service):
        """Test filtering with None values in data."""
        prompts = {
            0: {
                'data': {
                    'title': 'Test',
                    'prompt': 'Content',
                    'note': None,
                    'category': None,
                    'tags': None,
                    'favorite': None
                }
            }
        }

        # Should handle None values gracefully
        filtered = filter_service.filter_prompts(
            prompts,
            search_term="Test",
            filter_favorites=False
        )

        assert len(filtered) == 1

    def test_filter_with_empty_tags_list(self, filter_service, empty_data_service, sample_prompt_data):
        """Test filtering prompts with empty tags list."""
        prompt_data = sample_prompt_data(tags=[])
        empty_data_service.add_new_prompt(prompt_data)

        prompts = empty_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, filter_tag="any_tag")

        assert len(filtered) == 0

    def test_search_with_partial_match(self, filter_service, empty_data_service, sample_prompt_data):
        """Test search with partial string match."""
        prompt_data = sample_prompt_data(title="Testing Functionality")
        empty_data_service.add_new_prompt(prompt_data)

        prompts = empty_data_service.prompts
        filtered = filter_service.filter_prompts(prompts, search_term="Test")

        assert len(filtered) == 1

    def test_case_sensitive_default_is_false(self, filter_service, empty_data_service, sample_prompt_data):
        """Test that default case sensitivity is False."""
        prompt_data = sample_prompt_data(title="UPPERCASE")
        empty_data_service.add_new_prompt(prompt_data)

        prompts = empty_data_service.prompts
        # Don't specify case_sensitive parameter
        filtered = filter_service.filter_prompts(prompts, search_term="uppercase")

        assert len(filtered) == 1

    def test_filter_with_no_category_string(self, filter_service, empty_data_service, sample_prompt_data):
        """Test filtering prompts with 'No category' category."""
        prompt_data = sample_prompt_data(category="")
        empty_data_service.add_new_prompt(prompt_data)

        # Manually set to trigger 'No category' logic
        prompt_id = 0
        empty_data_service.prompts[prompt_id]['data']['category'] = None

        prompts = empty_data_service.prompts
        filtered = filter_service.filter_prompts(prompts)

        # Should handle None category
        assert len(filtered) == 1
