# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Rendered-HTML snapshot tests guarding the god-file template decomposition.

These tests render the four oversized templates targeted by the
template/frontend god-file decomposition (see
docs/IMPROVEMENT_PLAN_2026-08.md item #6) and compare the normalized output
against a stored baseline. As long as a phase's snapshot stays byte-identical
(after whitespace normalization), the extraction into `templates/macros/`
partials is behavior-preserving.

To regenerate baselines after an intentional markup change, delete the
relevant file(s) under tests/snapshots/ and re-run this module; the missing
baseline is written on first run instead of compared.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"

# Each entry: snapshot filename -> (route, requires_auth)
ROUTES: dict[str, tuple] = {
    "index.html.snapshot": ("/", True),
    "manage_tags.html.snapshot": ("/manage-tags", True),
    "manage_categories.html.snapshot": ("/manage-categories", True),
    "backup_management.html.snapshot": ("/backup-management", False),
}


def _normalize(html: str) -> str:
    """Collapse insignificant whitespace so snapshots aren't noisy.

    Collapses runs of whitespace to a single space and strips leading/
    trailing whitespace on each line, without altering tag structure or
    attribute order.
    """
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in html.splitlines()]
    return "\n".join(line for line in lines if line)


@pytest.fixture
def registered_user_with_client(api_client: TestClient) -> dict[str, object]:
    """Register a fresh user and return the client plus its access token.

    Mirrors the pattern in tests/test_history_navigation_auth.py: the
    TestClient does not auto-persist cookies from a JSON auth response, so
    the access_token must be passed explicitly per request.
    """
    response = api_client.post(
        "/api/auth/register",
        json={
            "username": "snapshotuser",
            "email": "snapshotuser@example.com",
            "password": "SecureP@ssw0rd123",
            "confirm_password": "SecureP@ssw0rd123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    return {**data, "client": api_client}


class TestTemplateSnapshots:
    """Snapshot every route targeted by the template decomposition plan."""

    @pytest.mark.parametrize(
        "snapshot_name,route,requires_auth",
        [(name, route, auth) for name, (route, auth) in ROUTES.items()],
    )
    def test_route_matches_snapshot(
        self,
        snapshot_name: str,
        route: str,
        requires_auth: bool,
        api_client: TestClient,
        registered_user_with_client: dict[str, object],
    ) -> None:
        if requires_auth:
            client: TestClient = registered_user_with_client["client"]  # type: ignore[assignment]
            access_token = registered_user_with_client["access_token"]
            response = client.get(
                route,
                cookies={"access_token": access_token},
                follow_redirects=False,
            )
        else:
            response = api_client.get(route, follow_redirects=False)

        assert (
            response.status_code == 200
        ), f"{route} returned {response.status_code}, expected 200"

        actual = _normalize(response.text)
        snapshot_path = SNAPSHOT_DIR / snapshot_name

        if not snapshot_path.exists():
            snapshot_path.write_text(actual, encoding="utf-8")
            pytest.skip(f"Baseline snapshot written for {route}: {snapshot_path}")

        expected = _normalize(snapshot_path.read_text(encoding="utf-8"))
        assert actual == expected, (
            f"Rendered output for {route} no longer matches the stored "
            f"snapshot at {snapshot_path}. If this change is intentional, "
            "delete the snapshot file and re-run to regenerate it."
        )
