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


class TestVersionWorkflow:
    """Integration tests for complete version control workflows"""

    def test_create_update_view_workflow(self, client, test_data_service):
        """Test: Create prompt -> Update it -> View history"""
        # Step 1: Create a new prompt
        create_response = client.post(
            "/api/prompts",
            data={
                "title": "Workflow Test Prompt",
                "prompt": "Initial content",
                "category": "Workflow",
                "tags": "test",
            },
        )
        assert create_response.status_code == 200
        prompt_id = create_response.json()["prompt_id"]

        # Step 2: Get initial version history
        history_response = client.get(f"/api/prompts/{prompt_id}/versions")
        assert history_response.status_code == 200
        initial_versions = history_response.json()["versions"]
        assert len(initial_versions) >= 1
        initial_version_id = initial_versions[0]["version_id"]

        # Step 3: Update the prompt
        update_response = client.put(
            f"/api/prompts/{prompt_id}",
            data={
                "title": "Updated Workflow Test",
                "prompt": "Updated content with more details",
                "category": "Workflow",
                "tags": "test,updated",
                "commit_message": "Added more details to the prompt",
            },
        )
        assert update_response.status_code == 200

        # Step 4: Get updated version history
        updated_history = client.get(f"/api/prompts/{prompt_id}/versions").json()
        assert len(updated_history["versions"]) > len(initial_versions)

        # Step 5: Verify latest version has correct message
        latest_version = updated_history["versions"][0]
        assert latest_version["message"] == "Added more details to the prompt"

    def test_compare_and_revert_workflow(self, client, test_data_service):
        """Test: Create -> Update -> Compare -> Revert workflow"""
        prompt_id = list(test_data_service.prompts.keys())[0]

        # Get initial version
        history1 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        initial_version_id = history1["versions"][-1]["version_id"]

        # Make first update
        client.put(
            f"/api/prompts/{prompt_id}",
            data={
                "title": "First Update",
                "prompt": "First update content",
                "category": "Testing",
                "tags": "",
                "commit_message": "First modification",
            },
        )

        # Get version after first update
        history2 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        first_update_version_id = history2["versions"][0]["version_id"]

        # Make second update
        client.put(
            f"/api/prompts/{prompt_id}",
            data={
                "title": "Second Update",
                "prompt": "Second update content",
                "category": "Testing",
                "tags": "",
                "commit_message": "Second modification",
            },
        )

        # Get version after second update
        history3 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        second_update_version_id = history3["versions"][0]["version_id"]

        # Compare first and second updates
        compare_response = client.get(
            f"/api/prompts/{prompt_id}/versions/compare?v1={first_update_version_id}&v2={second_update_version_id}"
        )
        assert compare_response.status_code == 200
        diff = compare_response.json()
        assert "changes" in diff
        assert "title" in diff["changes"] or "prompt" in diff["changes"]

        # Revert to initial version
        revert_response = client.post(
            f"/api/prompts/{prompt_id}/versions/{initial_version_id}/revert",
            data={"commit_message": "Reverting to initial state"},
        )
        assert revert_response.status_code == 200
        assert revert_response.json()["success"] is True

        # Verify revert created new version
        final_history = client.get(f"/api/prompts/{prompt_id}/versions").json()
        latest = final_history["versions"][0]
        assert latest["message"] == "Reverting to initial state"

    def test_multiple_updates_version_chain(self, client, test_data_service):
        """Test: Multiple updates create proper version chain"""
        prompt_id = list(test_data_service.prompts.keys())[0]

        # Make 5 sequential updates
        for i in range(5):
            client.put(
                f"/api/prompts/{prompt_id}",
                data={
                    "title": f"Update {i+1}",
                    "prompt": f"Content update {i+1}",
                    "category": "Testing",
                    "tags": "",
                    "commit_message": f"Update number {i+1}",
                },
            )

        # Get final version history
        history = client.get(f"/api/prompts/{prompt_id}/versions").json()
        versions = history["versions"]

        # Verify we have at least 6 versions (initial + 5 updates)
        assert len(versions) >= 6

        # Verify messages are in correct order (newest first)
        assert versions[0]["message"] == "Update number 5"
        assert versions[1]["message"] == "Update number 4"
        assert versions[2]["message"] == "Update number 3"
        assert versions[3]["message"] == "Update number 2"
        assert versions[4]["message"] == "Update number 1"

    def test_diff_with_multiple_field_changes(self, client, test_data_service):
        """Test: Diff correctly identifies changes in multiple fields"""
        prompt_id = list(test_data_service.prompts.keys())[0]

        # Get initial version
        history1 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        v1_id = history1["versions"][0]["version_id"]

        # Update multiple fields
        client.put(
            f"/api/prompts/{prompt_id}",
            data={
                "title": "Completely New Title",
                "prompt": "Completely new prompt content",
                "category": "NewCategory",
                "tags": "new,tags,here",
                "commit_message": "Changed everything",
            },
        )

        # Get new version
        history2 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        v2_id = history2["versions"][0]["version_id"]

        # Compare versions
        compare_response = client.get(
            f"/api/prompts/{prompt_id}/versions/compare?v1={v1_id}&v2={v2_id}"
        )
        assert compare_response.status_code == 200
        diff = compare_response.json()

        # Verify all changed fields are in diff
        changes = diff["changes"]
        assert "title" in changes
        assert "prompt" in changes
        assert "category" in changes
        assert "tags" in changes

    def test_revert_creates_new_version(self, client, test_data_service):
        """Test: Reverting creates a new version, not replacing"""
        prompt_id = list(test_data_service.prompts.keys())[0]

        # Get initial version count
        history1 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        initial_count = len(history1["versions"])
        initial_version_id = history1["versions"][-1]["version_id"]

        # Make an update
        client.put(
            f"/api/prompts/{prompt_id}",
            data={
                "title": "Modified",
                "prompt": "Modified content",
                "category": "Testing",
                "tags": "",
                "commit_message": "Modification",
            },
        )

        # Verify version count increased
        history2 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        assert len(history2["versions"]) == initial_count + 1

        # Revert to initial
        client.post(
            f"/api/prompts/{prompt_id}/versions/{initial_version_id}/revert",
            data={"commit_message": "Reverting"},
        )

        # Verify version count increased again (new version created)
        history3 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        assert len(history3["versions"]) == initial_count + 2

        # Verify latest version is the revert
        latest = history3["versions"][0]
        assert latest["message"] == "Reverting"

    def test_version_metadata_accuracy(self, client, test_data_service):
        """Test: Version metadata (timestamp, author) is accurate"""
        prompt_id = list(test_data_service.prompts.keys())[0]

        # Get version history
        history = client.get(f"/api/prompts/{prompt_id}/versions").json()
        versions = history["versions"]

        # Verify each version has required metadata
        for version in versions:
            assert "version_id" in version
            assert "timestamp" in version
            assert "author" in version
            assert "message" in version
            assert "parents" in version

            # Verify timestamp is valid ISO format
            assert "T" in version["timestamp"]
            assert "Z" in version["timestamp"]

            # Verify author is not empty
            assert len(version["author"]) > 0

    def test_concurrent_version_operations(self, client, test_data_service):
        """Test: Multiple version operations work correctly"""
        prompt_id = list(test_data_service.prompts.keys())[0]

        # Get initial version
        history1 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        v1_id = history1["versions"][0]["version_id"]

        # Update 1
        client.put(
            f"/api/prompts/{prompt_id}",
            data={
                "title": "Update 1",
                "prompt": "Content 1",
                "category": "Testing",
                "tags": "",
                "commit_message": "Update 1",
            },
        )

        history2 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        v2_id = history2["versions"][0]["version_id"]

        # Update 2
        client.put(
            f"/api/prompts/{prompt_id}",
            data={
                "title": "Update 2",
                "prompt": "Content 2",
                "category": "Testing",
                "tags": "",
                "commit_message": "Update 2",
            },
        )

        history3 = client.get(f"/api/prompts/{prompt_id}/versions").json()
        v3_id = history3["versions"][0]["version_id"]

        # Compare v1 and v2
        compare1 = client.get(
            f"/api/prompts/{prompt_id}/versions/compare?v1={v1_id}&v2={v2_id}"
        )
        assert compare1.status_code == 200

        # Compare v2 and v3
        compare2 = client.get(
            f"/api/prompts/{prompt_id}/versions/compare?v1={v2_id}&v2={v3_id}"
        )
        assert compare2.status_code == 200

        # Compare v1 and v3
        compare3 = client.get(
            f"/api/prompts/{prompt_id}/versions/compare?v1={v1_id}&v2={v3_id}"
        )
        assert compare3.status_code == 200

        # All comparisons should have changes
        assert len(compare1.json()["changes"]) > 0
        assert len(compare2.json()["changes"]) > 0
        assert len(compare3.json()["changes"]) > 0


class TestVersionErrorHandling:
    """Test error handling in version operations"""

    def test_invalid_version_id_comparison(self, client, test_data_service):
        """Test: Comparing with invalid version IDs returns error"""
        response = client.get("/api/prompts/0/versions/compare?v1=invalid1&v2=invalid2")
        assert response.status_code == 404

    def test_invalid_prompt_id_for_versions(self, client):
        """Test: Invalid prompt ID returns error"""
        response = client.get("/api/prompts/99999/versions")
        assert response.status_code == 404

    def test_revert_nonexistent_version(self, client, test_data_service):
        """Test: Reverting nonexistent version returns error"""
        response = client.post(
            "/api/prompts/0/versions/nonexistent/revert",
            data={"commit_message": "Test"},
        )
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
