# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Helpers for skill API tests: users, auth headers, direct skill seeding."""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from fixtures.skills import build_fixtures as bf

DEFAULT_SKILL_FILES: dict[str, bytes] = {
    "SKILL.md": bf.SKILL_MD_VALID.encode(),
    "scripts/fill.py": b'print("hi")\n',
    "references/sample.bin": bf.BINARY_SAMPLE,
}


def _is_text(content: bytes) -> bool:
    if b"\x00" in content:
        return False
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


@dataclass
class SkillApi:
    """A TestClient plus helpers to create users and skills."""

    client: TestClient

    def make_user(self, user_id: str, username: str, role: str = "user") -> dict:
        """Create (if needed) a user and return Bearer headers for it."""
        from src.config import auth_config
        from src.config.auth_config import auth_settings
        from src.db.models.user import User
        from src.db.session import SessionLocal
        from src.services.auth.jwt_service import JWTService
        from src.services.auth.password_service import PasswordService

        email = f"{username}@example.com"
        session = SessionLocal()
        try:
            if not session.query(User).filter_by(id=user_id).first():
                session.add(
                    User(
                        id=user_id,
                        username=username,
                        email=email,
                        password_hash=PasswordService(auth_settings).hash_password(
                            "SeedUserP@ssw0rd123"
                        ),
                        role=role,
                        is_active=True,
                        email_verified=True,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                )
                session.commit()
        finally:
            session.close()
        token = JWTService(auth_config.auth_settings).generate_access_token(
            user_id=user_id, username=username, email=email, role=role
        )
        return {"Authorization": f"Bearer {token}"}

    def login(self, user_id: str, username: str, role: str = "user") -> dict:
        """Create a user and sign in for real, so the token has a live session.

        Some legacy endpoints (for example ``copy-with-version``) validate the
        session behind the token, which a hand-made token does not have.
        """
        self.make_user(user_id, username, role)
        response = self.client.post(
            "/api/auth/login",
            json={
                "username_or_email": username,
                "password": "SeedUserP@ssw0rd123",
            },
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def import_zip(
        self,
        data: bytes,
        headers: dict,
        filename: str = "pdf-tools.zip",
        **form: str,
    ):
        """POST an archive to ``/api/skills/import``."""
        return self.client.post(
            "/api/skills/import",
            headers=headers,
            files={"archive": (filename, data, "application/zip")},
            data=form,
        )

    def seed_skill(
        self,
        owner_id: str,
        title: str = "Seeded skill",
        files: dict[str, bytes] | None = None,
        identifier: str = "seeded-skill",
        description: str | None = "A seeded skill",
        warnings: list[str] | None = None,
    ) -> int:
        """Insert a skill straight through the models, bypassing the service."""
        from src.db.models import Prompt
        from src.db.repositories.skill_repository import SkillRepository
        from src.db.session import SessionLocal

        file_map = files if files is not None else DEFAULT_SKILL_FILES
        skill_md = file_map["SKILL.md"].decode("utf-8", errors="replace")
        session = SessionLocal()
        try:
            prompt = Prompt(
                title=title,
                prompt=skill_md,
                item_type="skill",
                user_id=owner_id,
                legacy_public=False,
                favorite=False,
            )
            session.add(prompt)
            session.flush()
            records = [_Record(path, content) for path, content in file_map.items()]
            repo = SkillRepository(session)
            repo.insert_files(prompt.id, records)
            repo.upsert_package(
                prompt.id,
                skill_identifier=identifier,
                description=description,
                total_bytes=sum(r.size for r in records),
                file_count=len(records),
                format_warnings=warnings or [],
                source_archive_name=f"{identifier}.zip",
                files_updated_at=datetime.now(UTC),
            )
            session.commit()
            return prompt.id
        finally:
            session.close()

    def count_rows(self, table: str) -> int:
        """Count rows of a table through the app's session factory."""
        import sqlalchemy as sa

        from src.db.session import SessionLocal

        session = SessionLocal()
        try:
            return session.execute(
                sa.text(f"SELECT COUNT(*) FROM {table}")
            ).scalar_one()
        finally:
            session.close()


class _Record:
    """Duck-typed file record accepted by ``SkillRepository.insert_files``."""

    def __init__(self, path: str, content: bytes) -> None:
        self.path = path
        self.content = content
        self.size = len(content)
        self.sha256 = hashlib.sha256(content).hexdigest()
        self.is_text = _is_text(content)
