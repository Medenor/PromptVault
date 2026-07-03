# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for semantic_version Pydantic validator."""

import pytest
from pydantic import ValidationError

from src.web.models.requests import PromptCreateRequest, PromptUpdateRequest

# ============================================================================
# PromptCreateRequest
# ============================================================================


def make_create(**kwargs):
    defaults = {"title": "Test", "prompt": "Content"}
    defaults.update(kwargs)
    return PromptCreateRequest(**defaults)


def make_update(**kwargs):
    defaults = {"title": "Test", "prompt": "Content"}
    defaults.update(kwargs)
    return PromptUpdateRequest(**defaults)


class TestPromptCreateRequestSemanticVersion:
    def test_valid_1_0_0(self):
        req = make_create(semantic_version="1.0.0")
        assert req.semantic_version == "1.0.0"

    def test_valid_10_20_300(self):
        req = make_create(semantic_version="10.20.300")
        assert req.semantic_version == "10.20.300"

    def test_none_is_accepted(self):
        req = make_create(semantic_version=None)
        assert req.semantic_version is None

    def test_absent_defaults_to_none(self):
        req = make_create()
        assert req.semantic_version is None

    def test_empty_string_normalized_to_none(self):
        req = make_create(semantic_version="")
        assert req.semantic_version is None

    def test_whitespace_normalized_to_none(self):
        req = make_create(semantic_version="   ")
        assert req.semantic_version is None

    def test_whitespace_around_valid_version_stripped(self):
        req = make_create(semantic_version="  1.2.3  ")
        assert req.semantic_version == "1.2.3"

    def test_invalid_format_alpha_raises(self):
        with pytest.raises(ValidationError, match="MAJOR.MINOR.PATCH"):
            make_create(semantic_version="abc")

    def test_invalid_format_missing_patch_raises(self):
        with pytest.raises(ValidationError):
            make_create(semantic_version="1.0")

    def test_invalid_format_pre_release_raises(self):
        with pytest.raises(ValidationError):
            make_create(semantic_version="1.0.0-beta")

    def test_invalid_format_with_v_prefix_raises(self):
        with pytest.raises(ValidationError):
            make_create(semantic_version="v1.0.0")

    def test_invalid_format_extra_dots_raises(self):
        with pytest.raises(ValidationError):
            make_create(semantic_version="1.0.0.0")


class TestPromptUpdateRequestSemanticVersion:
    def test_valid_version(self):
        req = make_update(semantic_version="2.3.4")
        assert req.semantic_version == "2.3.4"

    def test_none_accepted(self):
        req = make_update(semantic_version=None)
        assert req.semantic_version is None

    def test_empty_string_normalized_to_none(self):
        req = make_update(semantic_version="")
        assert req.semantic_version is None

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError):
            make_update(semantic_version="not-a-version")

    def test_version_zero_components_valid(self):
        req = make_update(semantic_version="0.0.0")
        assert req.semantic_version == "0.0.0"
