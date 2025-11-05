import pytest
from pathlib import Path
import sys

# Ensure application package is importable when running tests directly
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def client(api_client_context):
    """Provide a TestClient bound to an isolated dataset."""
    return api_client_context["client"]


@pytest.fixture
def test_data_service(api_client_context):
    """Expose the isolated PromptDataService used by the API client."""
    return api_client_context["data_service"]


class TestVersionHistoryEndpoint:
    """Test GET /api/prompts/{id}/versions"""

    def test_get_version_history_success(self, client, test_data_service):
        """Test retrieving version history for a valid prompt"""
        response = client.get("/api/prompts/0/versions")
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert len(data["versions"]) >= 1

        # Check version structure
        version = data["versions"][0]
        assert "version_id" in version
        assert "timestamp" in version
        assert "author" in version
        assert "message" in version

    def test_get_version_history_invalid_id(self, client):
        """Test with invalid prompt ID"""
        response = client.get("/api/prompts/invalid/versions")
        assert response.status_code == 400
        assert "Invalid prompt ID" in response.json()["error"]

    def test_get_version_history_nonexistent_prompt(self, client):
        """Test with non-existent prompt ID"""
        response = client.get("/api/prompts/9999/versions")
        assert response.status_code == 404
        assert "Prompt not found" in response.json()["error"]


class TestGetSpecificVersionEndpoint:
    """Test GET /api/prompts/{id}/versions/{version_id}"""

    def test_get_specific_version_success(self, client, test_data_service):
        """Test retrieving a specific version"""
        # First get the version history to get a version_id
        history_response = client.get("/api/prompts/0/versions")
        versions = history_response.json()["versions"]
        version_id = versions[0]["version_id"]

        # Now get the specific version
        response = client.get(f"/api/prompts/0/versions/{version_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["version_id"] == version_id
        assert "data" in data
        assert "timestamp" in data

    def test_get_specific_version_invalid_prompt_id(self, client):
        """Test with invalid prompt ID"""
        response = client.get("/api/prompts/invalid/versions/some-version-id")
        assert response.status_code == 400

    def test_get_specific_version_nonexistent_version(self, client, test_data_service):
        """Test with non-existent version ID"""
        response = client.get("/api/prompts/0/versions/nonexistent-version-id")
        assert response.status_code == 404
        assert "Version not found" in response.json()["error"]


class TestCompareVersionsEndpoint:
    """Test GET /api/prompts/{id}/versions/compare"""

    def test_compare_versions_success(self, client, test_data_service):
        """Test comparing two versions"""
        # Get version history
        history_response = client.get("/api/prompts/0/versions")
        versions = history_response.json()["versions"]

        if len(versions) >= 1:
            version_id = versions[0]["version_id"]
            # Compare version with itself (should show no changes)
            response = client.get(
                f"/api/prompts/0/versions/compare?v1={version_id}&v2={version_id}"
            )
            assert response.status_code == 200
            data = response.json()
            assert "v1_id" in data
            assert "v2_id" in data
            assert "changes" in data

    def test_compare_versions_missing_parameters(self, client, test_data_service):
        """Test with missing version IDs"""
        response = client.get("/api/prompts/0/versions/compare")
        assert response.status_code == 400
        assert "Both v1 and v2 version IDs are required" in response.json()["error"]

    def test_compare_versions_invalid_prompt_id(self, client):
        """Test with invalid prompt ID"""
        response = client.get("/api/prompts/invalid/versions/compare?v1=id1&v2=id2")
        assert response.status_code == 400

    def test_compare_versions_nonexistent_version(self, client, test_data_service):
        """Test with non-existent version IDs"""
        response = client.get(
            "/api/prompts/0/versions/compare?v1=nonexistent1&v2=nonexistent2"
        )
        assert response.status_code == 404
        assert "One or both versions not found" in response.json()["error"]


class TestRevertVersionEndpoint:
    """Test POST /api/prompts/{id}/versions/{version_id}/revert"""

    def test_revert_version_success(self, client, test_data_service):
        """Test reverting to a previous version"""
        # Get version history
        history_response = client.get("/api/prompts/0/versions")
        versions = history_response.json()["versions"]

        if len(versions) >= 1:
            version_id = versions[0]["version_id"]

            # Revert to this version
            response = client.post(
                f"/api/prompts/0/versions/{version_id}/revert",
                data={"commit_message": "Test revert"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "new_version_id" in data

    def test_revert_version_invalid_prompt_id(self, client):
        """Test with invalid prompt ID"""
        response = client.post(
            "/api/prompts/invalid/versions/some-id/revert",
            data={"commit_message": "Test"},
        )
        assert response.status_code == 400

    def test_revert_version_nonexistent_prompt(self, client):
        """Test with non-existent prompt"""
        response = client.post(
            "/api/prompts/9999/versions/some-id/revert", data={"commit_message": "Test"}
        )
        assert response.status_code == 404
        assert "Prompt not found" in response.json()["error"]

    def test_revert_version_nonexistent_version(self, client, test_data_service):
        """Test with non-existent version"""
        response = client.post(
            "/api/prompts/0/versions/nonexistent-id/revert",
            data={"commit_message": "Test"},
        )
        assert response.status_code == 404
        assert "Version not found" in response.json()["error"]


class TestUpdatePromptWithCommitMessage:
    """Test PUT /api/prompts/{id} with commit message"""

    def test_update_prompt_with_commit_message(self, client, test_data_service):
        """Test updating a prompt with a commit message"""
        response = client.put(
            "/api/prompts/0",
            data={
                "title": "Updated Title",
                "prompt": "Updated prompt content",
                "category": "Updated",
                "tags": "updated,test",
                "commit_message": "Updated the prompt",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify the version was created with the commit message
        history_response = client.get("/api/prompts/0/versions")
        versions = history_response.json()["versions"]
        latest_version = versions[0]
        assert latest_version["message"] == "Updated the prompt"

    def test_update_prompt_default_commit_message(self, client, test_data_service):
        """Test updating a prompt without explicit commit message"""
        response = client.put(
            "/api/prompts/0",
            data={
                "title": "Another Update",
                "prompt": "Another update",
                "category": "Test",
                "tags": "",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify default commit message was used
        history_response = client.get("/api/prompts/0/versions")
        versions = history_response.json()["versions"]
        latest_version = versions[0]
        assert latest_version["message"] == "Update"

    def test_update_nonexistent_prompt(self, client):
        """Test updating a non-existent prompt"""
        response = client.put(
            "/api/prompts/9999",
            data={
                "title": "Title",
                "prompt": "Content",
                "category": "Test",
                "tags": "",
            },
        )
        assert response.status_code == 404
        assert "Prompt not found" in response.json()["error"]


class TestVersionIntegration:
    """Integration tests for version control workflow"""

    def test_create_and_version_workflow(self, client, test_data_service):
        """Test complete workflow: create prompt, update it, view history"""
        # Create a new prompt
        create_response = client.post(
            "/api/prompts",
            data={
                "title": "Integration Test Prompt",
                "prompt": "Initial content",
                "category": "Integration",
                "tags": "test",
            },
        )
        assert create_response.status_code == 200
        prompt_id = create_response.json()["prompt_id"]

        # Get initial version history
        history1 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        initial_version_count = len(history1["versions"])

        # Update the prompt
        update_response = client.put(
            f"/api/prompts/{prompt_id}",
            data={
                "title": "Updated Title",
                "prompt": "Updated content",
                "category": "Integration",
                "tags": "test,updated",
                "commit_message": "First update",
            },
        )
        assert update_response.status_code == 200

        # Get updated version history
        history2 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        assert len(history2["versions"]) == initial_version_count + 1

        # Verify latest version has correct message
        latest = history2["versions"][0]
        assert latest["message"] == "First update"

    def test_revert_workflow(self, client, test_data_service):
        """Test revert workflow"""
        # Get initial version
        history1 = client.get("/api/prompts/0/versions").json()
        initial_version_id = history1["versions"][-1]["version_id"]  # Oldest version

        # Update the prompt
        client.put(
            "/api/prompts/0",
            data={
                "title": "Modified Title",
                "prompt": "Modified content",
                "category": "Test",
                "tags": "",
                "commit_message": "Modification",
            },
        )

        # Revert to initial version
        revert_response = client.post(
            f"/api/prompts/0/versions/{initial_version_id}/revert",
            data={"commit_message": "Reverting to initial"},
        )
        assert revert_response.status_code == 200
        assert revert_response.json()["success"] is True

        # Verify new version was created
        history2 = client.get("/api/prompts/0/versions").json()
        latest = history2["versions"][0]
        assert latest["message"] == "Reverting to initial"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
