# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Phase 4 monitoring tests for validation events."""

import json
from pathlib import Path


def test_monitor_tracks_prompt_validation(api_client_context, tmp_path):
    """Ensure validation monitor records successes and failures for prompts."""
    client = api_client_context["client"]
    temp_dir = Path(api_client_context["temp_dir"])
    metrics_file = temp_dir / "logs" / "validation_metrics.json"

    # Create authentication headers
    from src.config.auth_config import auth_settings
    from src.services.auth.jwt_service import JWTService
    jwt_service = JWTService(auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="api-test-user-id",
        username="apiuser",
        email="api@example.com",
        role="editor",
    )
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # Reset metrics file for deterministic assertions
    if metrics_file.exists():
        metrics_file.unlink()

    # Valid prompt creation (success)
    success_response = client.post(
        "/api/prompts",
        headers=auth_headers,
        data={
            "title": "Monitored Prompt",
            "prompt": "Observed content",
            "category": "Monitoring",
            "tags": "metrics,validation",
        },
    )
    assert success_response.status_code == 201

    # Invalid prompt (failure)
    failure_response = client.post(
        "/api/prompts",
        headers=auth_headers,
        data={
            "title": "",
            "prompt": "Missing title should fail",
            "category": "",
            "tags": "",
        },
    )
    assert failure_response.status_code == 422

    stats_response = client.get("/api/validation/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()

    assert stats["successes_by_endpoint"].get("/api/prompts", 0) >= 1
    assert stats["failures_by_endpoint"].get("/api/prompts", 0) >= 1
    assert stats["failure_rate"] > 0

    assert metrics_file.exists()
    on_disk = json.loads(metrics_file.read_text())
    assert on_disk["recent_failures"], "Recent failures should be persisted to disk"


def test_monitor_records_import_upload_failures(api_client_context, tmp_path):
    """Ensure upload validation failures are captured in monitoring."""
    client = api_client_context["client"]

    bad_file = tmp_path / "payload.exe"
    bad_file.write_text("binary-content")

    with bad_file.open("rb") as fh:
        response = client.post(
            "/api/import",
            data={"mode": "append"},
            files={"file": ("payload.exe", fh, "application/octet-stream")},
        )

    assert response.status_code in (400, 422)

    stats_response = client.get("/api/validation/stats")
    stats = stats_response.json()

    assert stats["failures_by_endpoint"].get("/api/import", 0) >= 1
    # At least one recent failure entry should concern the import endpoint
    assert any(
        failure.get("endpoint") == "/api/import"
        for failure in stats.get("recent_failures", [])
    )
