"""
Unit tests for PromptVersioningService covering version creation and metadata helpers.
"""

import re


class TestVersionIdentifiers:
    """Tests for ID, timestamp, and user helpers."""

    def test_generate_version_id_returns_uuid(self, versioning_service):
        version_id = versioning_service.generate_version_id()

        assert re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            version_id
        )

    def test_generate_version_ids_are_unique(self, versioning_service):
        assert versioning_service.generate_version_id() != versioning_service.generate_version_id()

    def test_get_current_timestamp_format(self, versioning_service):
        timestamp = versioning_service.get_current_timestamp()

        assert timestamp.endswith('Z')
        assert 'T' in timestamp

    def test_get_current_user_handles_errors(self, monkeypatch, versioning_service):
        monkeypatch.setattr('src.services.prompt_versioning_service.getpass.getuser', lambda: "tester")
        assert versioning_service.get_current_user() == "tester"

        def _raise_error():
            raise RuntimeError("failure")

        monkeypatch.setattr('src.services.prompt_versioning_service.getpass.getuser', _raise_error)
        assert versioning_service.get_current_user() == "unknown"


class TestVersionCreation:
    """Tests for creating versions."""

    def test_create_initial_version_embeds_metadata(self, monkeypatch, versioning_service):
        monkeypatch.setattr(
            'src.services.prompt_versioning_service.PromptVersioningService.generate_version_id',
            lambda self: "version-1"
        )
        monkeypatch.setattr(
            'src.services.prompt_versioning_service.PromptVersioningService.get_current_timestamp',
            lambda self: "2024-01-01T00:00:00Z"
        )
        monkeypatch.setattr(
            'src.services.prompt_versioning_service.PromptVersioningService.get_current_user',
            lambda self: "tester"
        )

        data = {"title": "Prompt", "prompt": "Do something"}

        version = versioning_service.create_initial_version(data, commit_message="Initial import")

        assert version['version_id'] == "version-1"
        assert version['timestamp'] == "2024-01-01T00:00:00Z"
        assert version['author'] == "tester"
        assert version['message'] == "Initial import"
        assert version['parents'] == []
        assert version['data'] == data

    def test_create_new_version_sets_parent(self, monkeypatch, versioning_service):
        monkeypatch.setattr(
            'src.services.prompt_versioning_service.PromptVersioningService.generate_version_id',
            lambda self: "version-2"
        )
        monkeypatch.setattr(
            'src.services.prompt_versioning_service.PromptVersioningService.get_current_timestamp',
            lambda self: "2024-02-01T00:00:00Z"
        )
        monkeypatch.setattr(
            'src.services.prompt_versioning_service.PromptVersioningService.get_current_user',
            lambda self: "tester"
        )

        version = versioning_service.create_new_version(
            {"title": "Prompt v2"},
            parent_version_id="version-1",
            commit_message="Update content"
        )

        assert version['parents'] == ["version-1"]
        assert version['message'] == "Update content"


class TestVersionQueries:
    """Tests for helper methods that inspect prompt info."""

    def test_get_prompt_versions_returns_list(self, versioning_service):
        prompt_info = {'versions': [{'version_id': 'v1'}, {'version_id': 'v2'}]}

        versions = versioning_service.get_prompt_versions(prompt_info)

        assert len(versions) == 2

    def test_get_prompt_versions_missing_field(self, versioning_service):
        assert versioning_service.get_prompt_versions({}) == []

    def test_get_latest_version_id(self, versioning_service):
        prompt_info = {'branches': {'main': 'v5', 'dev': 'v3'}}

        assert versioning_service.get_latest_version_id(prompt_info) == 'v5'

    def test_get_latest_version_id_missing_branch(self, versioning_service):
        assert versioning_service.get_latest_version_id({}) is None


class TestRevertToVersion:
    """Tests for revert helper."""

    def test_revert_to_version_creates_new_version(self, monkeypatch, versioning_service):
        monkeypatch.setattr(
            'src.services.prompt_versioning_service.PromptVersioningService.generate_version_id',
            lambda self: "new-version"
        )
        monkeypatch.setattr(
            'src.services.prompt_versioning_service.PromptVersioningService.get_current_timestamp',
            lambda self: "2024-03-01T00:00:00Z"
        )
        monkeypatch.setattr(
            'src.services.prompt_versioning_service.PromptVersioningService.get_current_user',
            lambda self: "tester"
        )

        prompt_info = {'branches': {'main': 'current-version'}}
        reverted_data = {"title": "Previous", "prompt": "Old content"}

        new_version = versioning_service.revert_to_version(prompt_info, reverted_data, "Revert message")

        assert new_version['version_id'] == "new-version"
        assert new_version['parents'] == ['current-version']
        assert new_version['message'] == "Revert message"
        assert new_version['data'] == reverted_data
