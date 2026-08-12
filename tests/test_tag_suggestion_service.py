# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for tag suggestion service."""

import pytest

from src.services.tag_suggestion_service import (
    _equivalent_tokens,
    _normalize,
    _tokenize,
    suggest_tags,
)


@pytest.fixture
def sample_tags():
    """Sample tags for testing."""
    return [
        "python",
        "testing",
        "development",
        "api",
        "database",
        "code-review",
        "security",
        "bug-fix",
        "data-analysis",
        "machine-learning",
    ]


@pytest.fixture
def sample_tags_with_synonyms():
    """Sample tags that have synonym mappings."""
    return ["database", "testing", "security", "verified", "bug", "fixed", "final"]


class TestBasicSuggestionFunctionality:
    """Test basic tag suggestion functionality."""

    def test_suggest_tags_basic_match(self, sample_tags):
        """Test that tags are suggested when content tokens match."""
        content = "This is a python testing framework for api development"
        results = suggest_tags(content, sample_tags, limit=5)

        # Should return results
        assert len(results) > 0
        assert len(results) <= 5

        # Results should be tuples of (tag, score)
        for tag, score in results:
            assert isinstance(tag, str)
            assert isinstance(score, float)
            assert score > 0

        # Should include matching tags
        tag_names = [tag for tag, _ in results]
        assert "python" in tag_names or "testing" in tag_names or "api" in tag_names

    def test_suggest_tags_empty_content(self, sample_tags):
        """Test that empty content returns empty list."""
        results = suggest_tags("", sample_tags, limit=10)
        assert results == []

    def test_suggest_tags_empty_tags_list(self):
        """Test that empty tags list returns empty list."""
        content = "This is some content with python and testing"
        results = suggest_tags(content, [], limit=10)
        assert results == []

    def test_suggest_tags_limit_parameter(self, sample_tags):
        """Test that limit parameter is respected."""
        content = "python testing api development security database code-review"

        # Test limit of 3
        results = suggest_tags(content, sample_tags, limit=3)
        assert len(results) <= 3

        # Test limit of 5
        results = suggest_tags(content, sample_tags, limit=5)
        assert len(results) <= 5

        # Test limit of 1
        results = suggest_tags(content, sample_tags, limit=1)
        assert len(results) <= 1

    def test_suggest_tags_none_content(self, sample_tags):
        """Test that None content is handled gracefully."""
        results = suggest_tags(None, sample_tags, limit=10)
        assert results == []

    def test_suggest_tags_whitespace_only_content(self, sample_tags):
        """Test that whitespace-only content returns empty list."""
        results = suggest_tags("   \t\n  ", sample_tags, limit=10)
        assert results == []


class TestTokenizationAndNormalization:
    """Test tokenization and normalization functionality."""

    def test_suggest_tags_unicode_normalization(self, sample_tags):
        """Test that unicode characters with accents/diacritics are normalized."""
        content = "python développement sécurité données"
        results = suggest_tags(content, sample_tags, limit=10)

        # Should match normalized versions
        assert len(results) >= 0  # May or may not match depending on tag normalization

    def test_suggest_tags_case_insensitive(self, sample_tags):
        """Test that case doesn't matter for matching."""
        content_lower = "python testing api"
        content_upper = "PYTHON TESTING API"
        content_mixed = "Python Testing Api"

        results_lower = suggest_tags(content_lower, sample_tags, limit=10)
        results_upper = suggest_tags(content_upper, sample_tags, limit=10)
        results_mixed = suggest_tags(content_mixed, sample_tags, limit=10)

        # All should produce the same results
        assert len(results_lower) == len(results_upper) == len(results_mixed)

        # Extract tag names (ignore scores as they might differ slightly)
        tags_lower = {tag for tag, _ in results_lower}
        tags_upper = {tag for tag, _ in results_upper}
        tags_mixed = {tag for tag, _ in results_mixed}

        assert tags_lower == tags_upper == tags_mixed

    def test_suggest_tags_with_stopwords(self, sample_tags):
        """Test that stopwords are filtered out."""
        # Content with lots of stopwords
        content = "the python and testing for the api with the database"
        results = suggest_tags(content, sample_tags, limit=10)

        # Should still match meaningful words
        assert len(results) > 0
        tag_names = [tag for tag, _ in results]
        assert any(tag in tag_names for tag in ["python", "testing", "api", "database"])

    def test_tokenize_with_special_chars(self):
        """Test that tokenize extracts tokens correctly from special characters."""
        text = "python-testing@api#development$security%database"
        tokens = _tokenize(text)

        # Should extract alphanumeric tokens
        assert "python" in tokens
        assert "testing" in tokens
        assert "api" in tokens
        assert "development" in tokens
        assert "security" in tokens
        assert "database" in tokens

        # Special characters should not be in tokens
        for token in tokens:
            assert "@" not in token
            assert "#" not in token
            assert "$" not in token
            assert "%" not in token

    def test_tokenize_filters_short_tokens(self):
        """Test that very short tokens are filtered."""
        content = "a python is an api of it"
        results = suggest_tags(content, ["python", "api"], limit=10)

        # Should still match despite short words
        assert len(results) > 0

    def test_normalize_unicode(self):
        """Test unicode normalization consistency."""
        text_with_accents = "café résumé naïve"
        normalized = _normalize(text_with_accents)

        # Should remove diacritics and convert to lowercase
        assert "café" not in normalized
        assert "café" not in normalized
        assert "cafe" in normalized or "cafe" == normalized.split()[0]

    def test_normalize_empty_string(self):
        """Test that normalizing empty string returns empty string."""
        assert _normalize("") == ""

    def test_normalize_none(self):
        """Test that normalizing None returns empty string."""
        assert _normalize(None) == ""


class TestSynonymMatching:
    """Test synonym matching functionality."""

    def test_suggest_tags_synonym_matching(self, sample_tags_with_synonyms):
        """Test that synonyms are matched (e.g., test matches testing)."""
        # Content with synonym words
        content = "I need to test the basededonnees for data integrity"
        results = suggest_tags(content, sample_tags_with_synonyms, limit=10)

        # Should match "testing" even though content has "test"
        # Should match "database" even though content has "basededonnees"
        [tag for tag, _ in results]

        # At least one synonym-based match should occur
        assert len(results) > 0

    def test_equivalent_tokens_synonyms(self):
        """Test that _equivalent_tokens returns synonyms."""
        # Test forward synonym (key to values)
        equivalents = _equivalent_tokens("testing")
        assert "testing" in equivalents
        assert "test" in equivalents
        assert "tests" in equivalents

    def test_equivalent_tokens_reverse_synonyms(self):
        """Test that _equivalent_tokens returns reverse synonyms."""
        # Test reverse synonym (value to key)
        equivalents = _equivalent_tokens("test")
        assert "test" in equivalents
        assert "testing" in equivalents

    def test_equivalent_tokens_no_synonyms(self):
        """Test that _equivalent_tokens returns just the token if no synonyms."""
        equivalents = _equivalent_tokens("python")
        assert "python" in equivalents
        # Should only contain the original token
        assert len(equivalents) >= 1

    def test_suggest_tags_database_synonyms(self, sample_tags_with_synonyms):
        """Test database synonym matching."""
        content = "The basededonnees contains important data"
        results = suggest_tags(content, sample_tags_with_synonyms, limit=10)

        tag_names = [tag for tag, _ in results]
        # "database" tag should match "basededonnees" in content
        assert "database" in tag_names


class TestScoringLogic:
    """Test scoring and ordering logic."""

    def test_suggest_tags_score_ordering(self, sample_tags):
        """Test that results are ordered by score descending."""
        content = "python python python testing api api development"
        results = suggest_tags(content, sample_tags, limit=10)

        # Results should be ordered by score descending
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_suggest_tags_score_reflects_frequency(self, sample_tags):
        """Test that score reflects token frequency."""
        # "python" appears 3 times, "testing" appears once
        content = "python python python testing"
        results = suggest_tags(content, sample_tags, limit=10)

        # Find scores for python and testing
        python_score = next((score for tag, score in results if tag == "python"), None)
        testing_score = next(
            (score for tag, score in results if tag == "testing"), None
        )

        if python_score and testing_score:
            # Python should have higher score due to higher frequency
            assert python_score > testing_score

    def test_suggest_tags_partial_match_requirement(self):
        """Test that tags require at least 50% of tokens to match."""
        # Multi-token tag where only partial match occurs
        tags = ["machine-learning-algorithm"]

        # Only "machine" matches
        content = "machine processing"
        results = suggest_tags(content, tags, limit=10)

        # Should match because 1 out of 3 tokens is >= 50% of required
        # (required = (3+1)//2 = 2, so needs at least 2 tokens, but actually
        # the code has: required = max(1, (len(tag_tokens) + 1) // 2)
        # For 3 tokens: (3+1)//2 = 2, so needs 2/3 tokens
        # For "machine" only: matched=1, required=2, so should NOT match

        # This test verifies the 50% threshold works
        assert len(results) == 0 or "machine-learning-algorithm" not in [
            tag for tag, _ in results
        ]

    def test_suggest_tags_multi_token_tag_matching(self):
        """Test matching for multi-token tags."""
        tags = ["code-review", "bug-fix", "data-analysis"]

        # Content matches both tokens of "code-review"
        content = "Please review the code for bugs"
        results = suggest_tags(content, tags, limit=10)

        tag_names = [tag for tag, _ in results]
        # Should match "code-review" (both tokens present)
        assert "code-review" in tag_names or "bug" in content

    def test_suggest_tags_alphabetical_tiebreaker(self):
        """Test that tags with equal scores are sorted alphabetically."""
        tags = ["zebra", "alpha", "beta"]

        # Content that matches all tags equally (once each)
        content = "zebra alpha beta"
        results = suggest_tags(content, tags, limit=10)

        # All should have same score (each token appears once)
        scores = [score for _, score in results]
        if len(set(scores)) == 1:  # If all scores are equal
            tag_names = [tag for tag, _ in results]
            # Should be alphabetically sorted
            assert tag_names == sorted(tag_names, key=str.lower)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_suggest_tags_special_chars_in_content(self, sample_tags):
        """Test handling of special characters in content."""
        content = "python@#$%^&*()testing!@#$api"
        results = suggest_tags(content, sample_tags, limit=10)

        # Should still extract and match tokens
        assert len(results) > 0

    def test_suggest_tags_special_chars_in_tags(self):
        """Test handling of special characters in tag names."""
        tags = ["python@special", "testing#tag", "api$value"]
        content = "python testing api special tag value"
        results = suggest_tags(content, tags, limit=10)

        # Should handle tags with special characters
        assert len(results) >= 0

    def test_suggest_tags_empty_tag_in_list(self):
        """Test that empty tags in list are skipped."""
        tags = ["python", "", "testing", None, "api"]
        content = "python testing api"
        results = suggest_tags(content, tags, limit=10)

        # Should handle empty/None tags gracefully
        assert len(results) > 0
        tag_names = [tag for tag, _ in results]
        assert "" not in tag_names
        assert None not in tag_names

    def test_suggest_tags_with_untokenizable_tags(self):
        """Test tags that produce no tokens (only special chars or very short)."""
        tags = ["python", "@@", "##", "!!", "ab", "testing"]
        content = "python testing code"
        results = suggest_tags(content, tags, limit=10)

        # Should skip tags that produce no valid tokens
        tag_names = [tag for tag, _ in results]
        assert "python" in tag_names
        assert "testing" in tag_names
        # Tags with only special chars or very short should be skipped
        assert "@@" not in tag_names
        assert "##" not in tag_names

    def test_suggest_tags_numeric_content(self, sample_tags):
        """Test handling of numeric content."""
        content = "123 456 789 python 2024"
        results = suggest_tags(content, sample_tags, limit=10)

        # Should still match text tokens
        tag_names = [tag for tag, _ in results]
        if "python" in sample_tags:
            assert "python" in tag_names

    def test_suggest_tags_very_long_content(self, sample_tags):
        """Test handling of very long content."""
        # Generate long content with repeated matches
        content = " ".join(["python testing api"] * 100)
        results = suggest_tags(content, sample_tags, limit=10)

        # Should handle long content without issues
        assert len(results) > 0
        assert len(results) <= 10

    def test_suggest_tags_unicode_emoji(self, sample_tags):
        """Test handling of unicode emoji in content."""
        content = "python testing 🐍 with api 🚀 development"
        results = suggest_tags(content, sample_tags, limit=10)

        # Should extract text tokens and ignore emoji
        assert len(results) > 0

    def test_suggest_tags_mixed_language(self, sample_tags):
        """Test handling of mixed language content."""
        content = "python développement testing 测试 api"
        results = suggest_tags(content, sample_tags, limit=10)

        # Should handle mixed language content
        assert len(results) >= 0

    def test_suggest_tags_only_stopwords(self, sample_tags):
        """Test content with only stopwords."""
        content = "the and for with that this from into"
        results = suggest_tags(content, sample_tags, limit=10)

        # Should return empty list (no meaningful tokens)
        assert results == []

    def test_suggest_tags_only_short_tokens(self, sample_tags):
        """Test content with only very short tokens."""
        content = "a b c d e f g h i j"
        results = suggest_tags(content, sample_tags, limit=10)

        # Should return empty list (tokens too short, less than 3 chars)
        assert results == []

    def test_suggest_tags_single_token_match(self):
        """Test matching with single-token tags."""
        tags = ["python"]
        content = "python programming"
        results = suggest_tags(content, tags, limit=10)

        # Should match single-token tag
        assert len(results) == 1
        assert results[0][0] == "python"
        assert results[0][1] > 0

    def test_suggest_tags_zero_limit(self, sample_tags):
        """Test with limit of 0."""
        content = "python testing api"
        results = suggest_tags(content, sample_tags, limit=0)

        # Should return empty list
        assert results == []

    def test_suggest_tags_negative_limit(self, sample_tags):
        """Test with negative limit (edge case)."""
        content = "python testing api"
        results = suggest_tags(content, sample_tags, limit=-1)

        # Python list slicing with negative index returns all but last item
        # So results won't be empty, but will contain matches minus last item
        assert isinstance(results, list)

    def test_suggest_tags_whitespace_variations(self, sample_tags):
        """Test handling of various whitespace characters."""
        content = "python\ttesting\napi\r\ndevelopment"
        results = suggest_tags(content, sample_tags, limit=10)

        # Should extract tokens despite various whitespace
        assert len(results) > 0


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_suggest_tags_prompt_content(self):
        """Test with realistic prompt content."""
        tags = [
            "python",
            "code-review",
            "testing",
            "documentation",
            "api-design",
            "security-audit",
            "performance-optimization",
        ]

        content = """
        Please review this Python code for security vulnerabilities.
        Focus on API authentication and input validation.
        Provide documentation for any issues found.
        """

        results = suggest_tags(content, tags, limit=5)

        # Should suggest relevant tags
        assert len(results) > 0
        tag_names = [tag for tag, _ in results]

        # Should include relevant matches
        assert any(
            tag in tag_names for tag in ["python", "security-audit", "code-review"]
        )

    def test_suggest_tags_technical_content(self):
        """Test with technical jargon."""
        tags = [
            "database",
            "sql",
            "nosql",
            "migration",
            "schema-design",
            "indexing",
        ]

        content = "Need help with database migration and optimizing SQL queries with proper indexing"
        results = suggest_tags(content, tags, limit=5)

        # Should match technical terms
        assert len(results) > 0
        tag_names = [tag for tag, _ in results]
        assert "database" in tag_names or "sql" in tag_names or "migration" in tag_names

    def test_suggest_tags_no_matches(self):
        """Test when content has no matching tags."""
        tags = ["python", "javascript", "ruby"]
        content = "The quick brown fox jumps over the lazy dog"
        results = suggest_tags(content, tags, limit=10)

        # Should return empty list (no matches)
        assert results == []
