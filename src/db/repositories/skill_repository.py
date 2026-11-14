# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Skill repository for PromptVault.

Data access for ``skill_packages`` and ``skill_files``. File contents are
deferred: list and metadata queries never load them. They are read for one
file at a time, or streamed one file at a time for exports.
"""

from collections.abc import Iterable, Iterator
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session, undefer

from src.db.models import SkillFile, SkillPackage


class SkillFileData(Protocol):
    """Structural type for a file to insert (matches ``ArchiveFile``).

    Read-only properties, so frozen dataclasses satisfy it.
    """

    @property
    def path(self) -> str: ...

    @property
    def content(self) -> bytes: ...

    @property
    def size(self) -> int: ...

    @property
    def sha256(self) -> str: ...

    @property
    def is_text(self) -> bool: ...


class SkillRepository:
    """Repository for skill packages and their files."""

    def __init__(self, session: Session):
        """Initialize SkillRepository.

        Args:
            session: Database session
        """
        self.session = session

    def get_package(self, prompt_id: int) -> SkillPackage | None:
        """Return the package row of a skill, or None."""
        return self.session.get(SkillPackage, prompt_id)

    def get_packages(self, prompt_ids: Iterable[int]) -> dict[int, SkillPackage]:
        """Return package rows keyed by prompt id (one query, for list pages)."""
        ids = list(prompt_ids)
        if not ids:
            return {}
        rows = (
            self.session.query(SkillPackage)
            .filter(SkillPackage.prompt_id.in_(ids))
            .all()
        )
        return {row.prompt_id: row for row in rows}

    def upsert_package(
        self,
        prompt_id: int,
        *,
        skill_identifier: str,
        description: str | None,
        total_bytes: int,
        file_count: int,
        format_warnings: list[str],
        source_archive_name: str,
        files_updated_at: datetime,
    ) -> SkillPackage:
        """Create or update the package row of a skill."""
        values: dict[str, Any] = {
            "skill_identifier": skill_identifier,
            "description": description,
            "total_bytes": total_bytes,
            "file_count": file_count,
            "format_warnings": list(format_warnings),
            "source_archive_name": source_archive_name,
            "files_updated_at": files_updated_at,
        }
        package = self.get_package(prompt_id)
        if package is None:
            package = SkillPackage(prompt_id=prompt_id, **values)
            self.session.add(package)
        else:
            for key, value in values.items():
                setattr(package, key, value)
        self.session.flush()
        return package

    def list_files(self, prompt_id: int) -> list[SkillFile]:
        """List a skill's files ordered by path, without loading ``content``."""
        return (
            self.session.query(SkillFile)
            .filter(SkillFile.prompt_id == prompt_id)
            .order_by(SkillFile.path_folded, SkillFile.path)
            .all()
        )

    def get_file(self, prompt_id: int, path: str) -> SkillFile | None:
        """Return one file with its ``content`` loaded, or None."""
        return (
            self.session.query(SkillFile)
            .options(undefer(SkillFile.content))
            .filter(SkillFile.prompt_id == prompt_id, SkillFile.path == path)
            .first()
        )

    def iter_file_contents(self, prompt_id: int) -> Iterator[tuple[str, bytes]]:
        """Yield ``(path, content)`` one file at a time, ordered by path.

        Only one file's bytes are held by the repository at once, so exporting
        a large skill does not load every file into memory together.
        """
        rows = (
            self.session.query(SkillFile.id, SkillFile.path)
            .filter(SkillFile.prompt_id == prompt_id)
            .order_by(SkillFile.path_folded, SkillFile.path)
            .all()
        )
        for file_id, path in rows:
            content = (
                self.session.query(SkillFile.content)
                .filter(SkillFile.id == file_id)
                .scalar()
            )
            yield path, bytes(content)

    def insert_files(self, prompt_id: int, files: Iterable[SkillFileData]) -> int:
        """Insert files for a skill and return how many were added."""
        count = 0
        for file in files:
            self.session.add(
                SkillFile(
                    prompt_id=prompt_id,
                    path=file.path,
                    path_folded=file.path.casefold(),
                    size=file.size,
                    sha256=file.sha256,
                    is_text=file.is_text,
                    content=file.content,
                )
            )
            count += 1
        self.session.flush()
        return count

    def delete_files(self, prompt_id: int) -> int:
        """Delete every file of a skill and return how many were removed."""
        deleted = (
            self.session.query(SkillFile)
            .filter(SkillFile.prompt_id == prompt_id)
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return deleted
