"""
Integration-style tests for FastAPI endpoints covering CRUD, filters, and import/export flows.
"""

import io
import json
from pathlib import Path

import pytest


@pytest.fixture
def api_client(api_client_context):
    """Convenience fixture returning the FastAPI test client."""
    return api_client_context['client']


@pytest.fixture
def api_data_service(api_client_context):
    """Access to the underlying PromptDataService used by the API."""
    return api_client_context['data_service']


class TestPromptCrudEndpoints:
    """CRUD endpoint coverage."""

    def test_get_prompts_returns_seed_data(self, api_client):
        response = api_client.get("/api/prompts")
        assert response.status_code == 200
        data = response.json()['prompts']
        assert len(data) == 2
        assert data['0']['title'] == "API Prompt 1"

    def test_create_prompt_success(self, api_client):
        response = api_client.post(
            "/api/prompts",
            data={
                "title": "Created Prompt",
                "prompt": "Generated content",
                "category": "Testing",
                "tags": "new,creation"
            }
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload['success'] is True
        assert isinstance(payload['prompt_id'], int)

    def test_create_prompt_trims_tag_whitespace(self, api_client):
        response = api_client.post(
            "/api/prompts",
            data={
                "title": "Tagged Prompt",
                "prompt": "Body",
                "category": "Testing",
                "tags": "vision, creativity ,  focus  , ,"
            }
        )
        assert response.status_code == 200
        prompt_id = response.json()['prompt_id']

        retrieved = api_client.get(f"/api/prompts/{prompt_id}")
        assert retrieved.status_code == 200
        assert retrieved.json()['tags'] == ["vision", "creativity", "focus"]

    def test_create_prompt_validation_error(self, api_client):
        # Missing required 'prompt' field
        response = api_client.post("/api/prompts", data={"title": "Invalid"})
        assert response.status_code == 422

    def test_get_prompt_by_id(self, api_client):
        response = api_client.get("/api/prompts/0")
        assert response.status_code == 200
        data = response.json()
        assert data['title'] == "API Prompt 1"

    def test_get_prompt_not_found(self, api_client):
        response = api_client.get("/api/prompts/999")
        assert response.status_code == 404

    def test_get_prompt_invalid_id(self, api_client):
        response = api_client.get("/api/prompts/abc")
        assert response.status_code == 404

    def test_update_prompt_success(self, api_client):
        response = api_client.put(
            "/api/prompts/0",
            data={
                "title": "Updated Title",
                "prompt": "Updated body",
                "category": "Docs",
                "tags": "docs,api",
                "commit_message": "Update prompt"
            }
        )
        assert response.status_code == 200
        assert response.json()['success'] is True

        refreshed = api_client.get("/api/prompts/0")
        assert refreshed.json()['title'] == "Updated Title"

    def test_update_prompt_not_found(self, api_client):
        response = api_client.put(
            "/api/prompts/999",
            data={
                "title": "Missing",
                "prompt": "Body",
                "category": "",
                "tags": "",
                "commit_message": "test"
            }
        )
        assert response.status_code == 404

    def test_update_prompt_invalid_id(self, api_client):
        response = api_client.put(
            "/api/prompts/invalid",
            data={
                "title": "Invalid",
                "prompt": "Body",
                "category": "",
                "tags": "",
                "commit_message": "test"
            }
        )
        assert response.status_code == 400

    def test_delete_prompt_success(self, api_client):
        # Create prompt to delete
        create = api_client.post(
            "/api/prompts",
            data={
                "title": "Delete Me",
                "prompt": "Remove this",
                "category": "Temp",
                "tags": ""
            }
        )
        prompt_id = create.json()['prompt_id']

        response = api_client.delete(f"/api/prompts/{prompt_id}")
        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_delete_prompt_not_found(self, api_client):
        response = api_client.delete("/api/prompts/999")
        assert response.status_code == 200
        assert response.json()['success'] is False

    def test_delete_prompt_invalid_id(self, api_client):
        response = api_client.delete("/api/prompts/not-a-number")
        assert response.status_code == 400

    def test_toggle_favorite_success(self, api_client):
        response = api_client.put("/api/prompts/0/favorite")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert isinstance(data['favorite'], bool)

    def test_toggle_favorite_not_found(self, api_client):
        response = api_client.put("/api/prompts/999/favorite")
        assert response.status_code == 404

    def test_toggle_favorite_invalid_id(self, api_client):
        response = api_client.put("/api/prompts/abc/favorite")
        assert response.status_code == 400


class TestSearchAndFilterEndpoints:
    """Search endpoints covering combinations and edge cases."""

    def test_search_prompts_combined_filters(self, api_client):
        response = api_client.get("/api/prompts/search", params={
            "search": "API",
            "category": "Testing",
            "tag": "api",
            "favorites": False
        })
        assert response.status_code == 200
        results = response.json()['prompts']
        assert len(results) >= 1

    def test_search_prompts_favorites_only(self, api_client):
        response = api_client.get("/api/prompts/search", params={
            "favorites": True
        })
        assert response.status_code == 200
        results = response.json()['prompts']
        assert all(prompt['favorite'] is True for prompt in results.values())

    def test_search_prompts_case_sensitive(self, api_client):
        response = api_client.get("/api/prompts/search", params={
            "search": "api",
            "case_sensitive": True
        })
        assert response.status_code == 200
        assert response.json()['prompts'] == {}

    def test_search_prompts_no_results(self, api_client):
        response = api_client.get("/api/prompts/search", params={
            "search": "no-such-term"
        })
        assert response.status_code == 200
        assert response.json()['prompts'] == {}

    def test_search_prompts_invalid_bool(self, api_client):
        response = api_client.get("/api/prompts/search", params={"favorites": "not_bool"})
        assert response.status_code == 422


class TestCategoryAndTagEndpoints:
    """Category and tag endpoint validation."""

    def test_get_categories(self, api_client):
        response = api_client.get("/api/categories")
        assert response.status_code == 200
        categories = response.json()['categories']
        assert "Testing" in categories
        assert categories == sorted(categories)

    def test_get_tags(self, api_client):
        response = api_client.get("/api/tags")
        assert response.status_code == 200
        tags = response.json()['tags']
        assert "api" in tags


class TestExportEndpoints:
    """Import/export endpoint testing."""

    def test_export_prompts_csv(self, api_client):
        filename = "api_export_csv"
        response = api_client.post("/api/export", data={
            "format": "csv",
            "filename": filename,
            "include_favorites": False,
            "include_metadata": True
        })
        assert response.status_code == 200
        assert response.headers['content-disposition'].endswith('.csv"')

        export_path = Path("/tmp") / f"{filename}.csv"
        assert export_path.exists()
        export_path.unlink(missing_ok=True)

    def test_export_prompts_markdown(self, api_client):
        filename = "api_export_md"
        response = api_client.post("/api/export", data={
            "format": "markdown",
            "filename": filename,
            "include_favorites": False,
            "include_metadata": True
        })
        assert response.status_code == 200

        export_path = Path("/tmp") / f"{filename}.markdown"
        assert export_path.exists()
        export_path.unlink(missing_ok=True)

    def test_export_prompts_json(self, api_client):
        filename = "api_export_json"
        response = api_client.post("/api/export", data={
            "format": "json",
            "filename": filename,
            "include_favorites": False,
            "include_metadata": True
        })
        assert response.status_code == 200

        export_path = Path("/tmp") / f"{filename}.json"
        with open(export_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        assert payload['total_prompts'] >= 2
        export_path.unlink(missing_ok=True)

    def test_export_invalid_format_returns_error(self, api_client):
        response = api_client.post("/api/export", data={
            "format": "xml",
            "filename": "bad_export"
        })
        assert response.status_code == 400


class TestImportEndpoints:
    """Import scenarios for append/merge/replace and error handling."""

    def _post_import(self, api_client, filename, content_bytes, mode="append"):
        files = {
            "file": (filename, io.BytesIO(content_bytes), "text/csv")
        }
        data = {"mode": mode, "validate_data": True}
        response = api_client.post("/api/import", data=data, files=files)
        assert response.status_code == 200
        return response.json()

    def test_import_csv_append_mode(self, api_client, api_data_service):
        csv_content = (
            "title,prompt,note,category,tags,favorite\n"
            "Imported Prompt,Body,,Imported,\"tag1, tag2\",Yes\n"
        )
        result = self._post_import(api_client, "append.csv", csv_content.encode('utf-8'), mode="append")
        assert result['added_count'] == 1

        api_data_service.load_prompts()
        assert any(
            prompt['data']['title'] == "Imported Prompt"
            for prompt in api_data_service.prompts.values()
        )

    def test_import_csv_merge_mode(self, api_client, api_data_service):
        csv_content = (
            "title,prompt,note,category,tags,favorite\n"
            "API Prompt 1,Duplicate,,Testing,,No\n"
            "Unique Merge Prompt,Body,,Docs,,Yes\n"
        )
        result = self._post_import(api_client, "merge.csv", csv_content.encode('utf-8'), mode="merge")
        assert result['added_count'] == 1

        api_data_service.load_prompts()
        assert any(
            prompt['data']['title'] == "Unique Merge Prompt"
            for prompt in api_data_service.prompts.values()
        )

    def test_import_csv_replace_mode(self, api_client, api_data_service):
        csv_content = (
            "title,prompt,note,category,tags,favorite\n"
            "Replacement Prompt,Body,,Docs,,No\n"
        )
        result = self._post_import(api_client, "replace.csv", csv_content.encode('utf-8'), mode="replace")
        assert result['added_count'] == 1

        api_data_service.load_prompts()
        titles = [prompt['data']['title'] for prompt in api_data_service.prompts.values()]
        assert titles == ["Replacement Prompt"]

    def test_import_invalid_json_file(self, api_client):
        files = {
            "file": ("invalid.json", io.BytesIO(b"{not valid json}"), "application/json")
        }
        response = api_client.post("/api/import", data={"mode": "append"}, files=files)
        assert response.status_code == 500
        assert "Import failed" in response.json()['error']

    def test_import_empty_csv_file(self, api_client):
        csv_content = "title,prompt,note,category,tags,favorite\n"
        result = self._post_import(api_client, "empty.csv", csv_content.encode('utf-8'), mode="append")
        assert result['imported_count'] == 0


class TestImportExportStats:
    """Stats endpoint tests."""

    def test_get_import_export_stats(self, api_client):
        response = api_client.get("/api/import-export/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats['total_prompts'] >= 2
        assert stats['total_categories'] >= 1
        assert stats['total_tags'] >= 1
