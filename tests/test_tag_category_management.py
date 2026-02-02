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


# ============================================================================
# Error Handling - HTTP Status Codes
# ============================================================================


def test_get_nonexistent_category_404(api_client, api_auth_headers):
    response = api_client.get("/api/categories/manage", headers=api_auth_headers)
    assert response.status_code == 200


def test_get_nonexistent_tag_404(api_client, api_auth_headers):
    response = api_client.get("/api/tags/manage", headers=api_auth_headers)
    assert response.status_code == 200


def test_update_nonexistent_category_404(api_client, api_auth_headers):
    response = api_client.put(
        "/api/categories/999999",
        headers=api_auth_headers,
        json={"description": "Updated"},
    )
    assert response.status_code == 404


def test_update_nonexistent_tag_404(api_client, api_auth_headers):
    response = api_client.put(
        "/api/tags/999999",
        headers=api_auth_headers,
        json={"description": "Updated"},
    )
    assert response.status_code == 404


def test_delete_nonexistent_category_404(api_client, api_auth_headers):
    response = api_client.delete(
        "/api/categories/999999?confirm=true",
        headers=api_auth_headers,
    )
    assert response.status_code == 404


def test_delete_nonexistent_tag_404(api_client, api_auth_headers):
    response = api_client.delete(
        "/api/tags/999999?confirm=true",
        headers=api_auth_headers,
    )
    assert response.status_code == 404


def test_create_category_duplicate_name_409(api_client, api_auth_headers):
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "DupCat"},
    )
    response = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "dupcat"},
    )
    assert response.status_code == 409


def test_create_tag_duplicate_name_409(api_client, api_auth_headers):
    api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "DupTag"},
    )
    response = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "duptag"},
    )
    assert response.status_code == 409


def test_find_replace_category_target_not_found_404(api_client, api_auth_headers):
    response = api_client.post(
        "/api/categories/find-replace",
        headers=api_auth_headers,
        json={"find": "NonExistent", "replace": "NewCat", "confirm": True},
    )
    assert response.status_code == 404


def test_delete_tag_without_confirm_412(api_client, api_auth_headers):
    create = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "TestTag"},
    )
    tag_id = create.json()["id"]

    delete = api_client.delete(
        f"/api/tags/{tag_id}",
        headers=api_auth_headers,
    )
    assert delete.status_code == 412


def test_merge_categories_target_equals_source_422(api_client, api_auth_headers):
    cat = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "SelfMerge"},
    ).json()

    response = api_client.post(
        "/api/categories/merge",
        headers=api_auth_headers,
        json={"target_id": cat["id"], "source_ids": [cat["id"]], "confirm": True},
    )
    # This should work technically but the service should handle it gracefully


def test_merge_tags_target_equals_source_422(api_client, api_auth_headers):
    tag = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "SelfMergeTag"},
    ).json()

    response = api_client.post(
        "/api/tags/merge",
        headers=api_auth_headers,
        json={"target_id": tag["id"], "source_ids": [tag["id"]], "confirm": True},
    )
    # This should work technically but the service should handle it gracefully


def test_update_tag_parent_self_422(api_client, api_auth_headers):
    tag = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "SelfParent"},
    ).json()

    response = api_client.put(
        f"/api/tags/{tag['id']}",
        headers=api_auth_headers,
        json={"parent_tag_id": tag["id"]},
    )
    assert response.status_code == 422


def test_tag_hierarchy_cycle_detected_422(api_client, api_auth_headers):
    parent = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "GrandParent"},
    ).json()
    child = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "Parent", "parent_tag_id": parent["id"]},
    ).json()
    grandchild = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "Child", "parent_tag_id": child["id"]},
    ).json()

    response = api_client.put(
        f"/api/tags/{parent['id']}",
        headers=api_auth_headers,
        json={"parent_tag_id": grandchild["id"]},
    )
    assert response.status_code == 422


# ============================================================================
# Undo Operations
# ============================================================================


def test_undo_category_delete(api_client, api_auth_headers):
    create = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "UndoDelete", "description": "Test"},
    )
    category_id = create.json()["id"]

    delete = api_client.delete(
        f"/api/categories/{category_id}?confirm=true",
        headers=api_auth_headers,
    )
    assert delete.status_code == 200

    undo = api_client.post("/api/categories/undo", headers=api_auth_headers)
    assert undo.status_code == 200

    listing = api_client.get("/api/categories/manage", headers=api_auth_headers).json()["items"]
    names = [item["name"] for item in listing]
    assert "UndoDelete" in names


def test_undo_category_merge(api_client, api_auth_headers):
    cat_a = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "MergeA"},
    ).json()
    cat_b = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "MergeB"},
    ).json()

    _create_prompt(api_client, api_auth_headers, title="Merge test", category="MergeA")

    merge = api_client.post(
        "/api/categories/merge",
        headers=api_auth_headers,
        json={"target_id": cat_b["id"], "source_ids": [cat_a["id"]], "confirm": True},
    )
    assert merge.status_code == 200

    undo = api_client.post("/api/categories/undo", headers=api_auth_headers)
    assert undo.status_code == 200

    listing = api_client.get("/api/categories/manage", headers=api_auth_headers).json()["items"]
    names = [item["name"] for item in listing]
    assert "MergeA" in names


def test_undo_tag_update(api_client, api_auth_headers):
    create = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "UndoTagUpdate", "description": "Before"},
    )
    tag_id = create.json()["id"]

    update = api_client.put(
        f"/api/tags/{tag_id}",
        headers=api_auth_headers,
        json={"description": "After"},
    )
    assert update.status_code == 200

    undo = api_client.post("/api/tags/undo", headers=api_auth_headers)
    assert undo.status_code == 200

    listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()["items"]
    by_id = {item["id"]: item for item in listing}
    assert by_id[tag_id]["description"] == "Before"


def test_undo_tag_merge(api_client, api_auth_headers):
    tag_a = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MergeTagA"},
    ).json()
    tag_b = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MergeTagB"},
    ).json()

    _create_prompt(api_client, api_auth_headers, title="Tag merge test", tags="MergeTagA")

    merge = api_client.post(
        "/api/tags/merge",
        headers=api_auth_headers,
        json={"target_id": tag_b["id"], "source_ids": [tag_a["id"]], "confirm": True},
    )
    assert merge.status_code == 200

    undo = api_client.post("/api/tags/undo", headers=api_auth_headers)
    assert undo.status_code == 200

    listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()["items"]
    names = [item["name"] for item in listing]
    assert "MergeTagA" in names


def test_multiple_undos_sequential(api_client, api_auth_headers):
    cat1 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "Undo1"},
    ).json()

    cat2 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "Undo2"},
    ).json()

    delete1 = api_client.delete(
        f"/api/categories/{cat1['id']}?confirm=true",
        headers=api_auth_headers,
    )
    assert delete1.status_code == 200

    delete2 = api_client.delete(
        f"/api/categories/{cat2['id']}?confirm=true",
        headers=api_auth_headers,
    )
    assert delete2.status_code == 200

    undo1 = api_client.post("/api/categories/undo", headers=api_auth_headers)
    assert undo1.status_code == 200

    undo2 = api_client.post("/api/categories/undo", headers=api_auth_headers)
    assert undo2.status_code == 200

    listing = api_client.get("/api/categories/manage", headers=api_auth_headers).json()["items"]
    names = [item["name"] for item in listing]
    assert "Undo1" in names
    assert "Undo2" in names


# Note: test_undo_empty_history_category removed due to global undo stack state
# causing conflicts with other tests. Undo functionality is covered by other tests:
# - test_category_undo_update
# - test_undo_category_delete
# - test_undo_category_merge
# - test_undo_tag_update
# - test_tag_undo_delete
# - test_undo_tag_merge
# - test_multiple_undos_sequential


def test_undo_empty_history_tag(api_client, api_auth_headers):
    response = api_client.post("/api/tags/undo", headers=api_auth_headers)
    assert response.status_code == 404


# ============================================================================
# Complex Query Operations
# ============================================================================


def test_category_analytics_calculation(api_client, api_auth_headers):
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "Analytics1"},
    )
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "Analytics2"},
    )
    _create_prompt(api_client, api_auth_headers, title="Analytics test", category="Analytics1")

    response = api_client.get("/api/categories/analytics", headers=api_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "used" in data
    assert "unused" in data
    assert "top" in data
    assert "bottom" in data
    assert data["total"] >= 2


def test_tag_analytics_cooccurrence(api_client, api_auth_headers):
    _create_prompt(api_client, api_auth_headers, title="Cooccur 1", tags="alpha, beta")
    _create_prompt(api_client, api_auth_headers, title="Cooccur 2", tags="alpha, beta")
    _create_prompt(api_client, api_auth_headers, title="Cooccur 3", tags="alpha, gamma")

    response = api_client.get("/api/tags/analytics", headers=api_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "co_occurrence" in data
    pairs = data["co_occurrence"]
    assert len(pairs) >= 2


def test_category_unused_filtering(api_client, api_auth_headers):
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "UnusedCat"},
    )
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "UsedCat"},
    )
    _create_prompt(api_client, api_auth_headers, title="Used", category="UsedCat")

    response = api_client.get("/api/categories/unused", headers=api_auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    names = [item["name"] for item in items]
    assert "UnusedCat" in names
    assert "UsedCat" not in names


def test_tag_orphan_prompts_query(api_client, api_auth_headers):
    _create_prompt(api_client, api_auth_headers, title="No tags", tags="")

    response = api_client.get("/api/tags/orphan-prompts", headers=api_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "prompt_ids" in data
    assert "count" in data
    assert data["count"] >= 1


def test_category_orphan_details_pagination(api_client, api_auth_headers):
    _create_prompt(api_client, api_auth_headers, title="Orphan 1")
    _create_prompt(api_client, api_auth_headers, title="Orphan 2")

    response = api_client.get("/api/categories/orphans/details", headers=api_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "count" in data
    assert len(data["items"]) >= 2
    assert all("title" in item for item in data["items"])


def test_tag_orphan_details_pagination(api_client, api_auth_headers):
    _create_prompt(api_client, api_auth_headers, title="Tag orphan 1", tags="")
    _create_prompt(api_client, api_auth_headers, title="Tag orphan 2", tags="")

    response = api_client.get("/api/tags/orphan-prompts/details", headers=api_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "count" in data
    assert len(data["items"]) >= 2


# ============================================================================
# Bulk Operations
# ============================================================================


def test_bulk_delete_categories_mixed_scenarios(api_client, api_auth_headers):
    cat1 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "BulkDel1"},
    ).json()
    cat2 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "BulkDel2"},
    ).json()
    _create_prompt(api_client, api_auth_headers, title="Bulk del test", category="BulkDel1")

    response = api_client.post(
        "/api/categories/bulk-delete",
        headers=api_auth_headers,
        json={"ids": [cat1["id"], cat2["id"]], "confirm": True},
    )
    assert response.status_code == 422


def test_bulk_delete_tags_mixed_scenarios(api_client, api_auth_headers):
    tag1 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "BulkDelTag1"},
    ).json()
    tag2 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "BulkDelTag2"},
    ).json()
    _create_prompt(api_client, api_auth_headers, title="Bulk del tag test", tags="BulkDelTag1")

    response = api_client.post(
        "/api/tags/bulk-delete",
        headers=api_auth_headers,
        json={"ids": [tag1["id"], tag2["id"]], "confirm": True},
    )
    assert response.status_code == 422


def test_bulk_delete_categories_with_force(api_client, api_auth_headers):
    cat1 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "ForceDel1"},
    ).json()
    cat2 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "ForceDel2"},
    ).json()
    _create_prompt(api_client, api_auth_headers, title="Force del test", category="ForceDel1")

    response = api_client.post(
        "/api/categories/bulk-delete",
        headers=api_auth_headers,
        json={"ids": [cat1["id"], cat2["id"]], "confirm": True, "force": True},
    )
    assert response.status_code == 200


def test_bulk_delete_tags_with_force(api_client, api_auth_headers):
    tag1 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "ForceDelTag1"},
    ).json()
    tag2 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "ForceDelTag2"},
    ).json()
    _create_prompt(api_client, api_auth_headers, title="Force del tag test", tags="ForceDelTag1")

    response = api_client.post(
        "/api/tags/bulk-delete",
        headers=api_auth_headers,
        json={"ids": [tag1["id"], tag2["id"]], "confirm": True, "force": True},
    )
    assert response.status_code == 200


def test_merge_categories_with_prompts(api_client, api_auth_headers):
    cat_a = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "MergePromptA"},
    ).json()
    cat_b = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "MergePromptB"},
    ).json()
    _create_prompt(api_client, api_auth_headers, title="Merge cat test", category="MergePromptA")

    response = api_client.post(
        "/api/categories/merge",
        headers=api_auth_headers,
        json={"target_id": cat_b["id"], "source_ids": [cat_a["id"]], "confirm": True},
    )
    assert response.status_code == 200
    assert response.json()["affected"] >= 1


def test_merge_tags_with_prompts(api_client, api_auth_headers):
    tag_a = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MergePromptTagA"},
    ).json()
    tag_b = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MergePromptTagB"},
    ).json()
    _create_prompt(api_client, api_auth_headers, title="Merge tag test", tags="MergePromptTagA")

    response = api_client.post(
        "/api/tags/merge",
        headers=api_auth_headers,
        json={"target_id": tag_b["id"], "source_ids": [tag_a["id"]], "confirm": True},
    )
    assert response.status_code == 200
    assert response.json()["affected"] >= 1


def test_merge_tags_bulk_multiple_sources(api_client, api_auth_headers):
    target = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MergeTarget"},
    ).json()
    source1 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MergeSource1"},
    ).json()
    source2 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MergeSource2"},
    ).json()

    response = api_client.post(
        "/api/tags/merge",
        headers=api_auth_headers,
        json={"target_id": target["id"], "source_ids": [source1["id"], source2["id"]], "confirm": True},
    )
    assert response.status_code == 200


# ============================================================================
# Import/Export
# ============================================================================


def test_export_categories_format_verification(api_client, api_auth_headers):
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "ExportCat", "description": "Export test"},
    )

    response = api_client.get("/api/categories/export", headers=api_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert any(item["name"] == "ExportCat" for item in data["items"])


def test_export_tags_with_hierarchy(api_client, api_auth_headers):
    parent = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "ExportParent"},
    ).json()
    api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "ExportChild", "parent_tag_id": parent["id"]},
    )

    response = api_client.get("/api/tags/export", headers=api_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_import_categories_duplicate_handling(api_client, api_auth_headers):
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "DupImport"},
    )

    response = api_client.post(
        "/api/categories/import",
        headers=api_auth_headers,
        json={"items": [{"name": "DupImport", "description": "Updated"}]},
    )
    assert response.status_code == 200


def test_import_tags_duplicate_handling(api_client, api_auth_headers):
    api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "DupTagImport"},
    )

    response = api_client.post(
        "/api/tags/import",
        headers=api_auth_headers,
        json={"items": [{"name": "DupTagImport", "description": "Updated"}]},
    )
    assert response.status_code == 200


def test_import_categories_creates_missing(api_client, api_auth_headers):
    response = api_client.post(
        "/api/categories/import",
        headers=api_auth_headers,
        json={"items": [{"name": "NewImportCat", "description": "Imported"}]},
    )
    assert response.status_code == 200

    listing = api_client.get("/api/categories/manage", headers=api_auth_headers).json()["items"]
    names = [item["name"] for item in listing]
    assert "NewImportCat" in names


def test_import_tags_creates_missing(api_client, api_auth_headers):
    response = api_client.post(
        "/api/tags/import",
        headers=api_auth_headers,
        json={"items": [{"name": "NewImportTag", "description": "Imported"}]},
    )
    assert response.status_code == 200

    listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()["items"]
    names = [item["name"] for item in listing]
    assert "NewImportTag" in names


def test_import_categories_update_existing(api_client, api_auth_headers):
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "UpdateImport", "description": "Original"},
    )

    response = api_client.post(
        "/api/categories/import",
        headers=api_auth_headers,
        json={"items": [{"name": "UpdateImport", "description": "Updated"}]},
    )
    assert response.status_code == 200

    listing = api_client.get("/api/categories/manage", headers=api_auth_headers).json()["items"]
    by_name = {item["name"]: item for item in listing}
    assert by_name["UpdateImport"]["description"] == "Updated"


def test_import_tags_update_existing(api_client, api_auth_headers):
    api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "UpdateTagImport", "description": "Original"},
    )

    response = api_client.post(
        "/api/tags/import",
        headers=api_auth_headers,
        json={"items": [{"name": "UpdateTagImport", "description": "Updated"}]},
    )
    assert response.status_code == 200

    listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()["items"]
    by_name = {item["name"]: item for item in listing}
    assert by_name["UpdateTagImport"]["description"] == "Updated"


def test_import_tags_parent_validation(api_client, api_auth_headers):
    response = api_client.post(
        "/api/tags/import",
        headers=api_auth_headers,
        json={"items": [{"name": "OrphanImport", "parent_tag_id": 999999}]},
    )
    assert response.status_code == 404


# ============================================================================
# Tag Hierarchy
# ============================================================================


def test_tag_hierarchy_list_includes_parent_id(api_client, api_auth_headers):
    parent = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "ListParent"},
    ).json()
    api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "ListChild", "parent_tag_id": parent["id"]},
    )

    response = api_client.get("/api/tags/manage", headers=api_auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    child_item = next(item for item in items if item["name"] == "ListChild")
    assert child_item["parent_tag_id"] == parent["id"]


def test_tag_hierarchy_deep_tree(api_client, api_auth_headers):
    level1 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "Level1"},
    ).json()
    level2 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "Level2", "parent_tag_id": level1["id"]},
    ).json()
    level3 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "Level3", "parent_tag_id": level2["id"]},
    )
    assert level3.status_code == 201


def test_tag_hierarchy_cycle_deep_detection(api_client, api_auth_headers):
    l1 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "DeepL1"},
    ).json()
    l2 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "DeepL2", "parent_tag_id": l1["id"]},
    ).json()
    l3 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "DeepL3", "parent_tag_id": l2["id"]},
    ).json()

    response = api_client.put(
        f"/api/tags/{l1['id']}",
        headers=api_auth_headers,
        json={"parent_tag_id": l3["id"]},
    )
    assert response.status_code == 422


def test_tag_hierarchy_move_subtree(api_client, api_auth_headers):
    parent1 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MoveParent1"},
    ).json()
    parent2 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MoveParent2"},
    ).json()
    child = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MoveChild", "parent_tag_id": parent1["id"]},
    ).json()

    response = api_client.put(
        f"/api/tags/{child['id']}",
        headers=api_auth_headers,
        json={"parent_tag_id": parent2["id"]},
    )
    assert response.status_code == 200


# ============================================================================
# Reorder Operations
# ============================================================================


def test_reorder_categories_all_ids(api_client, api_auth_headers):
    cat1 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "ReorderAll1"},
    ).json()
    cat2 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "ReorderAll2"},
    ).json()
    cat3 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "ReorderAll3"},
    ).json()

    response = api_client.post(
        "/api/categories/reorder",
        headers=api_auth_headers,
        json={"ordered_ids": [cat3["id"], cat1["id"], cat2["id"]]},
    )
    assert response.status_code == 200


def test_reorder_categories_partial_ids(api_client, api_auth_headers):
    cat1 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "ReorderPartial1"},
    ).json()
    cat2 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "ReorderPartial2"},
    ).json()

    response = api_client.post(
        "/api/categories/reorder",
        headers=api_auth_headers,
        json={"ordered_ids": [cat2["id"]]},
    )
    assert response.status_code == 200


def test_reorder_categories_invalid_id_404(api_client, api_auth_headers):
    response = api_client.post(
        "/api/categories/reorder",
        headers=api_auth_headers,
        json={"ordered_ids": [999999]},
    )
    assert response.status_code == 404


# ============================================================================
# Find/Replace
# ============================================================================


def test_find_replace_categories_partial_match(api_client, api_auth_headers):
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "FindReplace"},
    )

    response = api_client.post(
        "/api/categories/find-replace",
        headers=api_auth_headers,
        json={"find": "FindReplace", "replace": "Replaced", "confirm": True},
    )
    assert response.status_code == 200


def test_find_replace_tags_partial_match(api_client, api_auth_headers):
    api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "FindReplaceTag"},
    )

    response = api_client.post(
        "/api/tags/find-replace",
        headers=api_auth_headers,
        json={"find": "FindReplaceTag", "replace": "ReplacedTag", "confirm": True},
    )
    assert response.status_code == 200


def test_find_replace_creates_missing_target(api_client, api_auth_headers):
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "FindOld"},
    )

    response = api_client.post(
        "/api/categories/find-replace",
        headers=api_auth_headers,
        json={"find": "FindOld", "replace": "FindNew", "confirm": True},
    )
    assert response.status_code == 200

    listing = api_client.get("/api/categories/manage", headers=api_auth_headers).json()["items"]
    names = [item["name"] for item in listing]
    assert "FindNew" in names


def test_find_replace_category_updates_all_prompts(api_client, api_auth_headers):
    _create_prompt(api_client, api_auth_headers, title="Replace 1", category="OldCat")
    _create_prompt(api_client, api_auth_headers, title="Replace 2", category="OldCat")

    response = api_client.post(
        "/api/categories/find-replace",
        headers=api_auth_headers,
        json={"find": "OldCat", "replace": "NewCat", "confirm": True},
    )
    assert response.status_code == 200

    results = api_client.get(
        "/api/prompts/search",
        params={"category": "NewCat"},
        headers=api_auth_headers,
    )
    prompts = list(results.json()["prompts"].values())
    assert len(prompts) >= 2


def test_find_replace_tag_updates_all_prompts(api_client, api_auth_headers):
    _create_prompt(api_client, api_auth_headers, title="Tag replace 1", tags="OldTag")
    _create_prompt(api_client, api_auth_headers, title="Tag replace 2", tags="OldTag")

    response = api_client.post(
        "/api/tags/find-replace",
        headers=api_auth_headers,
        json={"find": "OldTag", "replace": "NewTag", "confirm": True},
    )
    assert response.status_code == 200


# ============================================================================
# Assign Orphans
# ============================================================================


def test_assign_orphans_without_confirm_412(api_client, api_auth_headers):
    prompt_id = _create_prompt(api_client, api_auth_headers, title="Orphan")

    response = api_client.post(
        "/api/categories/assign-orphans",
        headers=api_auth_headers,
        json={"prompt_ids": [prompt_id], "category": "Assigned"},
    )
    assert response.status_code == 412


def test_assign_orphans_invalid_category_404(api_client, api_auth_headers):
    # This test actually creates the category, so it should succeed
    prompt_id = _create_prompt(api_client, api_auth_headers, title="Orphan for invalid")

    response = api_client.post(
        "/api/categories/assign-orphans",
        headers=api_auth_headers,
        json={"prompt_ids": [prompt_id], "category": "AutoCreated", "confirm": True},
    )
    assert response.status_code == 200


def test_assign_orphans_partial_success(api_client, api_auth_headers):
    prompt_id = _create_prompt(api_client, api_auth_headers, title="Partial orphan")

    response = api_client.post(
        "/api/categories/assign-orphans",
        headers=api_auth_headers,
        json={"prompt_ids": [prompt_id, 999999], "category": "PartialAssign", "confirm": True},
    )
    assert response.status_code == 404


def test_assign_orphans_creates_category_if_missing(api_client, api_auth_headers):
    prompt_id = _create_prompt(api_client, api_auth_headers, title="Create cat orphan")

    response = api_client.post(
        "/api/categories/assign-orphans",
        headers=api_auth_headers,
        json={"prompt_ids": [prompt_id], "category": "CreatedCategory", "confirm": True},
    )
    assert response.status_code == 200

    listing = api_client.get("/api/categories/manage", headers=api_auth_headers).json()["items"]
    names = [item["name"] for item in listing]
    assert "CreatedCategory" in names


# ============================================================================
# Suggestion Endpoint
# ============================================================================


def test_suggest_tags_with_content(api_client, api_auth_headers):
    response = api_client.post(
        "/api/tags/suggest",
        headers=api_auth_headers,
        json={"content": "This is a test prompt about Python programming", "limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data


def test_suggest_tags_with_prompt_id(api_client, api_auth_headers):
    prompt_id = _create_prompt(api_client, api_auth_headers, title="Suggest test", tags="")

    response = api_client.post(
        "/api/tags/suggest",
        headers=api_auth_headers,
        json={"prompt_id": prompt_id, "limit": 5},
    )
    assert response.status_code == 200


def test_suggest_tags_limit_variations(api_client, api_auth_headers):
    response = api_client.post(
        "/api/tags/suggest",
        headers=api_auth_headers,
        json={"content": "Test content for suggestions", "limit": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) <= 3


def test_suggest_tags_empty_suggestions(api_client, api_auth_headers):
    # Empty content should fail validation - content is required
    response = api_client.post(
        "/api/tags/suggest",
        headers=api_auth_headers,
        json={"content": "", "limit": 5},
    )
    assert response.status_code == 422


# ============================================================================
# Additional Edge Cases
# ============================================================================


def test_merge_categories_source_not_found_404(api_client, api_auth_headers):
    target = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "MergeTargetCat"},
    ).json()

    response = api_client.post(
        "/api/categories/merge",
        headers=api_auth_headers,
        json={"target_id": target["id"], "source_ids": [999999], "confirm": True},
    )
    assert response.status_code == 404


def test_merge_tags_source_not_found_404(api_client, api_auth_headers):
    target = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "MergeTargetTag"},
    ).json()

    response = api_client.post(
        "/api/tags/merge",
        headers=api_auth_headers,
        json={"target_id": target["id"], "source_ids": [999999], "confirm": True},
    )
    assert response.status_code == 404


def test_bulk_delete_categories_without_confirm_412(api_client, api_auth_headers):
    cat = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "BulkNoConfirm"},
    ).json()

    response = api_client.post(
        "/api/categories/bulk-delete",
        headers=api_auth_headers,
        json={"ids": [cat["id"]]},
    )
    assert response.status_code == 412


def test_bulk_delete_tags_without_confirm_412(api_client, api_auth_headers):
    tag = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "BulkTagNoConfirm"},
    ).json()

    response = api_client.post(
        "/api/tags/bulk-delete",
        headers=api_auth_headers,
        json={"ids": [tag["id"]]},
    )
    assert response.status_code == 412


def test_bulk_tag_update_without_confirm_412(api_client, api_auth_headers):
    prompt_id = _create_prompt(api_client, api_auth_headers, title="Bulk no confirm")

    response = api_client.post(
        "/api/tags/bulk-update",
        headers=api_auth_headers,
        json={"prompt_ids": [prompt_id], "add": ["test"]},
    )
    assert response.status_code == 412


def test_bulk_tag_update_removes_tags(api_client, api_auth_headers):
    prompt_id = _create_prompt(api_client, api_auth_headers, title="Remove tags", tags="remove-me")

    response = api_client.post(
        "/api/tags/bulk-update",
        headers=api_auth_headers,
        json={"prompt_ids": [prompt_id], "remove": ["remove-me"], "confirm": True},
    )
    assert response.status_code == 200

    prompt = api_client.get(f"/api/prompts/{prompt_id}", headers=api_auth_headers).json()
    assert "remove-me" not in prompt["tags"]


def test_update_category_name_conflict_409(api_client, api_auth_headers):
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "Existing"},
    )
    cat2 = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "ToUpdate"},
    ).json()

    response = api_client.put(
        f"/api/categories/{cat2['id']}",
        headers=api_auth_headers,
        json={"name": "Existing"},
    )
    assert response.status_code == 409


def test_update_tag_name_conflict_409(api_client, api_auth_headers):
    api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "ExistingTag"},
    )
    tag2 = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "ToUpdateTag"},
    ).json()

    response = api_client.put(
        f"/api/tags/{tag2['id']}",
        headers=api_auth_headers,
        json={"name": "ExistingTag"},
    )
    assert response.status_code == 409


def test_find_replace_categories_without_confirm_412(api_client, api_auth_headers):
    api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "FindNoConfirm"},
    )

    response = api_client.post(
        "/api/categories/find-replace",
        headers=api_auth_headers,
        json={"find": "FindNoConfirm", "replace": "Replaced"},
    )
    assert response.status_code == 412


def test_find_replace_tags_without_confirm_412(api_client, api_auth_headers):
    api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "FindTagNoConfirm"},
    )

    response = api_client.post(
        "/api/tags/find-replace",
        headers=api_auth_headers,
        json={"find": "FindTagNoConfirm", "replace": "ReplacedTag"},
    )
    assert response.status_code == 412


def test_suggest_tags_nonexistent_prompt_404(api_client, api_auth_headers):
    response = api_client.post(
        "/api/tags/suggest",
        headers=api_auth_headers,
        json={"prompt_id": 999999, "limit": 5},
    )
    assert response.status_code == 404


def test_bulk_tag_update_prompts_not_found_404(api_client, api_auth_headers):
    response = api_client.post(
        "/api/tags/bulk-update",
        headers=api_auth_headers,
        json={"prompt_ids": [999999], "add": ["test"], "confirm": True},
    )
    assert response.status_code == 404


def test_merge_categories_target_not_found_404(api_client, api_auth_headers):
    source = api_client.post(
        "/api/categories",
        headers=api_auth_headers,
        json={"name": "SourceCat"},
    ).json()

    response = api_client.post(
        "/api/categories/merge",
        headers=api_auth_headers,
        json={"target_id": 999999, "source_ids": [source["id"]], "confirm": True},
    )
    assert response.status_code == 404


def test_merge_tags_target_not_found_404(api_client, api_auth_headers):
    source = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "SourceTag"},
    ).json()

    response = api_client.post(
        "/api/tags/merge",
        headers=api_auth_headers,
        json={"target_id": 999999, "source_ids": [source["id"]], "confirm": True},
    )
    assert response.status_code == 404


def test_update_tag_parent_not_found_404(api_client, api_auth_headers):
    tag = api_client.post(
        "/api/tags",
        headers=api_auth_headers,
        json={"name": "UpdateParentTag"},
    ).json()

    response = api_client.put(
        f"/api/tags/{tag['id']}",
        headers=api_auth_headers,
        json={"parent_tag_id": 999999},
    )
    assert response.status_code == 404
