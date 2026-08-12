# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for scheduler admin endpoints."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.web.routers import scheduler as scheduler_router


class FakeScheduler:
    """Lightweight scheduler stub for API tests."""

    def __init__(self) -> None:
        self.is_running = False
        self._next_run = datetime(2026, 1, 21, 12, 0, 0, tzinfo=UTC)

    def start(self) -> None:
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def get_job_info(self) -> dict:
        if not self.is_running:
            return {}
        return {"next_run_time": self._next_run}

    def run_cleanup_now(self) -> dict:
        return {
            "success": True,
            "expired_found": 3,
            "timestamp": datetime(2026, 1, 21, 12, 30, 0, tzinfo=UTC).isoformat(),
        }


@pytest.fixture
def scheduler_override():
    """Override the global scheduler instance for API tests."""
    original = scheduler_router._session_cleanup_scheduler
    fake = FakeScheduler()
    scheduler_router._session_cleanup_scheduler = fake
    try:
        yield fake
    finally:
        scheduler_router._session_cleanup_scheduler = original


@pytest.fixture
def admin_headers(api_client):
    """Create admin auth headers for scheduler endpoints."""
    from datetime import timedelta

    from src.config.auth_config import auth_settings
    from src.db.models.user import User
    from src.db.models.user_session import UserSession
    from src.db.session import SessionLocal
    from src.services.auth.jwt_service import JWTService
    from src.services.auth.password_service import PasswordService

    password_service = PasswordService(auth_settings)
    password_hash = password_service.hash_password("AdminP@ssw0rd123")

    session = SessionLocal()
    try:
        admin = session.query(User).filter_by(id="scheduler-admin-id").first()
        if not admin:
            admin = User(
                id="scheduler-admin-id",
                username="scheduleradmin",
                email="scheduler-admin@example.com",
                password_hash=password_hash,
                role="admin",
                is_active=True,
                email_verified=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(admin)
            session.flush()

            admin_session = UserSession(
                user_id=admin.id,
                family_id="scheduler-admin-family",
                refresh_token_jti="scheduler-admin-jti",
                ip_address="127.0.0.1",
                device_info="Test Agent",
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=30),
                is_revoked=False,
            )
            session.add(admin_session)
            session.commit()
    finally:
        session.close()

    jwt_service = JWTService(auth_settings)
    token = jwt_service.generate_access_token(
        user_id="scheduler-admin-id",
        username="scheduleradmin",
        email="scheduler-admin@example.com",
        role="admin",
    )

    return {"Authorization": f"Bearer {token}"}


def test_get_scheduler_raises_when_unset():
    """Directly ensure get_scheduler reports missing instance."""
    scheduler_router._session_cleanup_scheduler = None
    with pytest.raises(HTTPException) as exc:
        scheduler_router.get_scheduler()
    assert exc.value.status_code == 503


def test_scheduler_status_returns_job_info(
    api_client, admin_headers, scheduler_override
):
    scheduler_override.start()
    response = api_client.get("/api/admin/scheduler/status", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["is_running"] is True
    assert payload["next_run_time"] is not None
    assert "job_info" in payload


def test_scheduler_start_and_stop_flow(api_client, admin_headers, scheduler_override):
    start_response = api_client.post(
        "/api/admin/scheduler/start", headers=admin_headers
    )
    assert start_response.status_code == 200
    assert start_response.json()["is_running"] is True

    stop_response = api_client.post("/api/admin/scheduler/stop", headers=admin_headers)
    assert stop_response.status_code == 200
    assert stop_response.json()["is_running"] is False


def test_scheduler_start_conflict_when_running(
    api_client, admin_headers, scheduler_override
):
    scheduler_override.start()
    response = api_client.post("/api/admin/scheduler/start", headers=admin_headers)
    assert response.status_code == 409


def test_scheduler_stop_conflict_when_stopped(
    api_client, admin_headers, scheduler_override
):
    scheduler_override.stop()
    response = api_client.post("/api/admin/scheduler/stop", headers=admin_headers)
    assert response.status_code == 409


def test_scheduler_cleanup_now_success(api_client, admin_headers, scheduler_override):
    response = api_client.post(
        "/api/admin/scheduler/cleanup-now", headers=admin_headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["expired_found"] == 3
    assert payload["deleted"] == 3
    assert payload["timestamp"]


def test_scheduler_cleanup_now_error(api_client, admin_headers, scheduler_override):
    def fail_cleanup():
        raise RuntimeError("boom")

    scheduler_override.run_cleanup_now = fail_cleanup
    response = api_client.post(
        "/api/admin/scheduler/cleanup-now", headers=admin_headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "boom"


def test_scheduler_status_response_requires_is_running():
    with pytest.raises(ValidationError):
        scheduler_router.SchedulerStatusResponse(next_run_time=None)


def test_cleanup_result_response_requires_timestamp():
    with pytest.raises(ValidationError):
        scheduler_router.CleanupResultResponse(success=True)
