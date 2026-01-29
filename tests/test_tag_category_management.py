# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for tag/category management endpoints."""

from typing import Dict


import pytest


@pytest.fixture
def api_client(api_client_context):
    return api_client_context["client"]


@pytest.fixture
def api_auth_headers(api_client_context) -> Dict[str, str]:
    """Create authentication headers with valid API user access token."""
    from src.services.auth.jwt_service import JWTService
    from src.config import auth_config

    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="api-test-user-id",
        username="apiuser",
        email="api@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {access_token}"}


def _create_prompt(api_client, api_auth_headers, title: str, category: str = "", tags: str = "") -> int:
    response = api_client.post(
        "/api/prompts",
        headers=api_auth_headers,
        data={
            "title": title,
            "prompt": "Sample content",
            "category": category,
            "tags": tags,
            "commit_message": "Create prompt",
        },
    )
    assert response.status_code == 201
    return response.json()["prompt_id"]


def test_category_crud_and_manage_list(api_client, api_auth_headers):
    create = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "Ops", "description": "Operations"},
    )
    assert create.status_code == 201
    created = create.json()

    listing = api_client.get("/api/categories/manage", headers=api_auth_headers)
    assert listing.status_code == 200
    names = [item["name"] for item in listing.json()["items"]]
    assert "Ops" in names

    update = api_client.put(
        f"/api/categories/{created['id']}",
        headers=api_auth_headers,
        json={"description": "Ops & Support"},
    )
    assert update.status_code == 200
    assert update.json()["description"] == "Ops & Support"

    delete = api_client.delete(
        f"/api/categories/{created['id']}?confirm=true",
        headers=api_auth_headers,
    )
    assert delete.status_code == 200


def test_category_delete_requires_confirm(api_client, api_auth_headers):
    create = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "Temp"},
    )
    category_id = create.json()["id"]

    delete = api_client.delete(
        f"/api/categories/{category_id}",
        headers=api_auth_headers,
    )
    assert delete.status_code == 412


def test_category_delete_force_clears_prompts(api_client, api_auth_headers):
    category = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "NeedsCleanup"},
    ).json()
    prompt_id = _create_prompt(api_client, api_auth_headers, title="Needs cleanup", category="NeedsCleanup")

    blocked = api_client.delete(
        f"/api/categories/{category['id']}?confirm=true",
        headers=api_auth_headers,
    )
    assert blocked.status_code == 422

    forced = api_client.delete(
        f"/api/categories/{category['id']}?confirm=true&force=true",
        headers=api_auth_headers,
    )
    assert forced.status_code == 200

    prompt = api_client.get(f"/api/prompts/{prompt_id}", headers=api_auth_headers).json()
    assert prompt["category"] == "No category"


def test_category_find_replace_updates_prompts(api_client, api_auth_headers):
    _create_prompt(api_client, api_auth_headers, title="Old category", category="Legacy")

    replace = api_client.post(
        "/api/categories/find-replace",
        headers=api_auth_headers,
        json={"find": "Legacy", "replace": "Modern", "confirm": True},
    )
    assert replace.status_code == 200

    categories = api_client.get("/api/categories/manage", headers=api_auth_headers).json()["items"]
    names = [item["name"] for item in categories]
    assert "Modern" in names
    assert "Legacy" not in names

    results = api_client.get(
        "/api/prompts/search",
        params={"category": "Modern"},
        headers=api_auth_headers,
    )
    assert results.status_code == 200
    prompts = results.json()["prompts"].values()
    assert any(prompt["category"] == "Modern" for prompt in prompts)


def test_category_orphans_returns_prompt_ids(api_client, api_auth_headers):
    prompt_id = _create_prompt(api_client, api_auth_headers, title="No category")

    response = api_client.get("/api/categories/orphans", headers=api_auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert prompt_id in payload["prompt_ids"]


def test_category_orphan_assign(api_client, api_auth_headers):
    prompt_id = _create_prompt(api_client, api_auth_headers, title="Assign me")

    assign = api_client.post(
        "/api/categories/assign-orphans",
        headers=api_auth_headers,
        json={"prompt_ids": [prompt_id], "category": "Assigned", "confirm": True},
    )
    assert assign.status_code == 200

    prompt = api_client.get(f"/api/prompts/{prompt_id}", headers=api_auth_headers).json()
    assert prompt["category"] == "Assigned"


def test_category_reorder_updates_sort_order(api_client, api_auth_headers):
    cat_a = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "OrderA"},
    ).json()
    cat_b = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "OrderB"},
    ).json()

    reorder = api_client.post(
        "/api/categories/reorder",
        headers=api_auth_headers,
        json={"ordered_ids": [cat_b["id"], cat_a["id"]]},
    )
    assert reorder.status_code == 200

    listing = api_client.get("/api/categories/manage", headers=api_auth_headers).json()["items"]
    by_id = {item["id"]: item for item in listing}
    assert by_id[cat_b["id"]]["sort_order"] == 1
    assert by_id[cat_a["id"]]["sort_order"] == 2


def test_tag_merge_requires_confirm(api_client, api_auth_headers):
    tag_a = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "alpha"},
    ).json()["id"]
    tag_b = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "beta"},
    ).json()["id"]

    merge = api_client.post(
        "/api/tags/merge",
        headers=api_auth_headers,
        json={"target_id": tag_b, "source_ids": [tag_a]},
    )
    assert merge.status_code == 412


def test_tag_orphans_lists_unused_tags(api_client, api_auth_headers):
    create = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "unused-tag"},
    )
    assert create.status_code == 201

    orphans = api_client.get("/api/tags/orphans", headers=api_auth_headers)
    assert orphans.status_code == 200
    names = [item["name"] for item in orphans.json()["items"]]
    assert "unused-tag" in names


def test_bulk_tag_update_adds_tags(api_client, api_auth_headers):
    prompt_id = _create_prompt(api_client, api_auth_headers, title="Bulk tag", tags="")

    update = api_client.post(
        "/api/tags/bulk-update",
        headers=api_auth_headers,
        json={"prompt_ids": [prompt_id], "add": ["bulk", "ops"], "confirm": True},
    )
    assert update.status_code == 200

    prompt = api_client.get(
        f"/api/prompts/{prompt_id}",
        headers=api_auth_headers,
    )
    assert prompt.status_code == 200
    tags = prompt.json()["tags"]
    assert "bulk" in tags
    assert "ops" in tags


def test_tag_suggest_requires_content(api_client, api_auth_headers):
    response = api_client.post(
        "/api/tags/suggest",
        headers=api_auth_headers,
        json={"limit": 5},
    )
    assert response.status_code == 422


def test_tag_create_conflict_case_insensitive(api_client, api_auth_headers):
    create = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "CaseTag"},
    )
    assert create.status_code == 201

    conflict = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "casetag"},
    )
    assert conflict.status_code == 409


def test_tag_import_export_roundtrip(api_client, api_auth_headers):
    create = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "exported", "description": "demo"},
    )
    assert create.status_code == 201

    exported = api_client.get("/api/tags/export", headers=api_auth_headers)
    assert exported.status_code == 200
    payload = exported.json()
    assert any(item["name"] == "exported" for item in payload["items"])

    imported = api_client.post(
        "/api/tags/import",
        headers=api_auth_headers,
        json={"items": [{"name": "imported", "description": "from file"}]},
    )
    assert imported.status_code == 200

    listing = api_client.get("/api/tags/manage", headers=api_auth_headers)
    names = [item["name"] for item in listing.json()["items"]]
    assert "imported" in names


def test_tag_analytics_includes_cooccurrence(api_client, api_auth_headers):
    _create_prompt(api_client, api_auth_headers, title="Pair one", tags="alpha, beta")
    _create_prompt(api_client, api_auth_headers, title="Pair two", tags="alpha, beta")

    analytics = api_client.get("/api/tags/analytics", headers=api_auth_headers)
    assert analytics.status_code == 200
    payload = analytics.json()
    pairs = payload.get("co_occurrence", [])
    assert any(
        pair["tag_a"] == "alpha" and pair["tag_b"] == "beta" and pair["count"] >= 2
        for pair in pairs
    )


def test_category_create_invalid_color(api_client, api_auth_headers):
    response = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "ColorFail", "color": "!!!"},
    )
    assert response.status_code == 422


def test_tag_import_requires_items(api_client, api_auth_headers):
    response = api_client.post(
        "/api/tags/import",
        headers=api_auth_headers,
        json={"items": []},
    )
    assert response.status_code == 422


def test_tag_create_invalid_name(api_client, api_auth_headers):
    response = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "invalid!tag"},
    )
    assert response.status_code == 422


def test_category_create_invalid_name(api_client, api_auth_headers):
    response = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "invalid@category"},
    )
    assert response.status_code == 422


def test_category_undo_update(api_client, api_auth_headers):
    create = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "UndoCat", "description": "Before"},
    )
    category_id = create.json()["id"]

    update = api_client.put(
        f"/api/categories/{category_id}",
        headers=api_auth_headers,
        json={"description": "After"},
    )
    assert update.status_code == 200

    undo = api_client.post("/api/categories/undo", headers=api_auth_headers)
    assert undo.status_code == 200

    listing = api_client.get("/api/categories/manage", headers=api_auth_headers).json()["items"]
    by_id = {item["id"]: item for item in listing}
    assert by_id[category_id]["description"] == "Before"


def test_tag_undo_delete(api_client, api_auth_headers):
    create = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "UndoTag"},
    )
    tag_id = create.json()["id"]

    delete = api_client.delete(
        f"/api/tags/{tag_id}?confirm=true",
        headers=api_auth_headers,
    )
    assert delete.status_code == 200

    undo = api_client.post("/api/tags/undo", headers=api_auth_headers)
    assert undo.status_code == 200

    listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()["items"]
    names = [item["name"] for item in listing]
    assert "UndoTag" in names


def test_tag_hierarchy_parent_assignment(api_client, api_auth_headers):
    parent = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "ParentTag"},
    ).json()

    child = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "ChildTag", "parent_tag_id": parent["id"]},
    )
    assert child.status_code == 201

    listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()["items"]
    child_item = next(item for item in listing if item["name"] == "ChildTag")
    assert child_item["parent_tag_id"] == parent["id"]


def test_tag_hierarchy_parent_not_found(api_client, api_auth_headers):
    response = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "OrphanChild", "parent_tag_id": 999999},
    )
    assert response.status_code == 404


def test_tag_hierarchy_cycle_prevented(api_client, api_auth_headers):
    parent = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "CycleParent"},
    ).json()
    child = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "CycleChild", "parent_tag_id": parent["id"]},
    ).json()

    update = api_client.put(
        f"/api/tags/{parent['id']}",
        headers=api_auth_headers,
        json={"parent_tag_id": child["id"]},
    )
    assert update.status_code == 422
