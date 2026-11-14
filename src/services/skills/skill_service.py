# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Skill service: import, read, export, edit, replace and delete skills.

A skill is a ``prompts`` row with ``item_type='skill'`` plus a ``skill_packages``
row and ``skill_files`` rows (data-model.md). This service owns every skill
operation and its audit events; routers stay thin and call it.

Archive bytes never touch the filesystem here: the reader works in memory and
file contents go straight into the database inside one transaction.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import IO, Any

from src.config import auth_config
from src.config.skill_config import SkillSettings, get_skill_settings
from src.db.models import Prompt, User
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.prompt_repository import PromptRepository
from src.db.repositories.skill_repository import SkillRepository
from src.db.repositories.tag_repository import TagRepository
from src.db.session import get_db_session
from src.services.exceptions import ItemIsPromptError
from src.services.logging_service import logging_service
from src.services.skills import errors as err
from src.services.skills.archive_reader import SKILL_MD, ReadArchive, SkillArchiveReader
from src.services.skills.archive_writer import write_skill_archive
from src.services.skills.errors import SkillArchiveError
from src.services.skills.frontmatter import SkillMetadata, parse_skill_md
from src.services.skills.markdown_renderer import render_instructions
from src.services.skills.serializers import skill_file_entry, skill_summary_dict
from src.web.validators import (
    MAX_CATEGORY_LENGTH,
    MAX_NOTE_LENGTH,
    MAX_TAG_COUNT,
    MAX_TAG_LENGTH,
    MAX_TITLE_LENGTH,
    sanitize_tags,
    sanitize_text_field,
)

logger = logging_service.get_logger(__name__)

_TAG_SPLIT = re.compile(r",")


class SkillLookupError(Exception):
    """A skill or one of its files does not exist or is not visible.

    Attributes:
        code: ``SKILL_NOT_FOUND`` or ``FILE_NOT_FOUND`` (API contract codes).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RawFile:
    """A stored file ready to be sent as a download."""

    path: str
    content: bytes


@dataclass(frozen=True)
class SkillExport:
    """A freshly built export archive.

    Attributes:
        identifier: Skill identifier; names the archive and its top folder.
        archive: Spooled temporary file positioned at the start; the caller
            must close it.
        size: Length of the archive in bytes.
    """

    identifier: str
    archive: IO[bytes]
    size: int


def _auth_enabled() -> bool:
    return bool(auth_config.auth_settings.auth_enabled)


def _is_admin(user: User | None) -> bool:
    return user is not None and user.role == "admin"


def split_tags(tags: str | list[str] | None) -> list[str]:
    """Normalise tags given as a comma-separated string or a list."""
    if not tags:
        return []
    raw = _TAG_SPLIT.split(tags) if isinstance(tags, str) else tags
    return sanitize_tags(
        [t.strip() for t in raw if isinstance(t, str) and t.strip()],
        max_count=MAX_TAG_COUNT,
        max_length_per_tag=MAX_TAG_LENGTH,
    )


def audit_skill_deleted(prompt: Prompt, actor: str | None = None) -> None:
    """Write the ``skill.delete`` audit event for a skill row being removed.

    Used by every delete path (skill endpoint, ``DELETE /api/prompts/{id}`` and
    bulk delete) so a skill is audited once however it is deleted (FR-025a).
    Does nothing for a prompt. File contents and names are never logged.
    """
    if prompt.item_type != "skill":
        return
    package = prompt.skill_package
    logging_service.log_audit_event(
        action="skill.delete",
        resource_type="skill",
        resource_id=str(prompt.id),
        actor=actor,
        skill_identifier=package.skill_identifier if package else None,
        file_count=package.file_count if package else None,
        total_bytes=package.total_bytes if package else None,
    )


class SkillService:
    """Business logic for skills."""

    def __init__(
        self,
        settings: SkillSettings | None = None,
        reader: SkillArchiveReader | None = None,
    ) -> None:
        self._settings = settings or get_skill_settings()
        self._reader = reader or SkillArchiveReader(self._settings)

    # ------------------------------------------------------------------ access

    def _load_skill(
        self, session: Any, skill_id: int, user: User | None, access: str
    ) -> Prompt:
        """Load a skill row the caller may use.

        Args:
            session: Open database session.
            skill_id: Item id.
            user: Acting user (None in anonymous mode).
            access: ``read`` (owner or admin), ``write`` (owner only, even for
                admins) or ``delete`` (owner or admin).

        Raises:
            SkillLookupError: Unknown id, or the caller may not use the skill
                (existence is hidden).
            ItemIsPromptError: The id is a prompt the caller can see.
        """
        prompt = PromptRepository(session).get_by_id(skill_id)
        not_found = SkillLookupError(err.SKILL_NOT_FOUND, "Skill not found")
        if prompt is None:
            raise not_found

        if _auth_enabled():
            owns = user is not None and prompt.user_id == user.id
            allowed = owns if access == "write" else owns or _is_admin(user)
            if prompt.item_type != "skill":
                visible = owns or _is_admin(user) or bool(prompt.legacy_public)
                if visible:
                    raise ItemIsPromptError(context={"prompt_id": skill_id})
                raise not_found
            if not allowed:
                raise not_found
        elif prompt.item_type != "skill":
            raise ItemIsPromptError(context={"prompt_id": skill_id})
        return prompt

    # ------------------------------------------------------------- serialising

    def _detail(self, session: Any, prompt: Prompt) -> dict[str, Any]:
        """Build the ``SkillDetail`` dict for a loaded skill."""
        repo = SkillRepository(session)
        detail = skill_summary_dict(prompt, repo.get_package(prompt.id))
        detail["note"] = prompt.note or ""
        detail["instructions_html"] = render_instructions(prompt.prompt)
        detail["files"] = [skill_file_entry(f) for f in repo.list_files(prompt.id)]
        return detail

    # ------------------------------------------------------------------- audit

    def _audit_rejected(
        self,
        action: str,
        archive_name: str,
        exc: SkillArchiveError,
        user: User | None,
        skill_id: int | None = None,
    ) -> None:
        logging_service.log_audit_event(
            action=action,
            resource_type="skill",
            resource_id=str(skill_id) if skill_id is not None else "none",
            status="failure",
            actor=user.username if user else None,
            archive_name=archive_name,
            reason_code=exc.code,
            offending_entry=exc.offending_entry,
        )

    # ------------------------------------------------------------------ import

    def _read_and_parse(
        self, upload_bytes: bytes, archive_name: str
    ) -> tuple[ReadArchive, SkillMetadata, bytes]:
        """Read the archive and parse ``SKILL.md``; raises ``SkillArchiveError``."""
        archive = self._reader.read(upload_bytes, archive_name)
        skill_md = next((f for f in archive.files if f.path == SKILL_MD), None)
        if skill_md is None:  # the reader guarantees this; defence in depth
            raise SkillArchiveError(err.SKILL_MD_MISSING, "SKILL.md not found")
        meta = parse_skill_md(
            skill_md.content, archive.wrapped_folder_name, archive_name
        )
        return archive, meta, skill_md.content

    def _store_archive(
        self,
        session: Any,
        prompt: Prompt,
        archive: ReadArchive,
        meta: SkillMetadata,
        archive_name: str,
        replace: bool,
    ) -> None:
        """Write files and the package row for ``prompt`` (inside the caller's transaction)."""
        repo = SkillRepository(session)
        if replace:
            repo.delete_files(prompt.id)
            session.expire(prompt, ["skill_files"])
        repo.insert_files(prompt.id, archive.files)
        repo.upsert_package(
            prompt.id,
            skill_identifier=meta.identifier,
            description=meta.description,
            total_bytes=sum(f.size for f in archive.files),
            file_count=len(archive.files),
            format_warnings=meta.warnings,
            source_archive_name=archive_name[:255],
            files_updated_at=datetime.now(UTC),
        )
        prompt.prompt = meta.text

    def import_skill(
        self,
        upload_bytes: bytes,
        archive_name: str,
        user: User | None,
        category: str | None = None,
        tags: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """Import a skill from a zip archive (FR-004 to FR-011).

        Everything is stored in one transaction: if anything fails, nothing is.

        Args:
            upload_bytes: Raw bytes of the uploaded archive.
            archive_name: Original file name of the upload.
            user: The importing user (owner of the new skill).
            category: Optional category name.
            tags: Optional tags, comma-separated or a list.

        Returns:
            dict: The new skill as ``SkillDetail``.

        Raises:
            SkillArchiveError: The archive was rejected (nothing was stored).
        """
        try:
            archive, meta, _ = self._read_and_parse(upload_bytes, archive_name)
        except SkillArchiveError as exc:
            self._audit_rejected("skill.import.rejected", archive_name, exc, user)
            raise

        with get_db_session() as session:
            category_name = (
                sanitize_text_field(
                    category, max_length=MAX_CATEGORY_LENGTH, allow_newlines=False
                )
                if category
                else ""
            )
            category_obj = (
                CategoryRepository(session).get_or_create(category_name)
                if category_name
                else None
            )
            tag_objects = (
                TagRepository(session).get_or_create_many(split_tags(tags))
                if tags
                else []
            )
            prompt = PromptRepository(session).create_with_tags(
                tag_objects,
                title=meta.title,
                prompt=meta.text,
                category_id=category_obj.id if category_obj else None,
                note="",
                favorite=False,
                legacy_public=False,
                item_type="skill",
                user_id=user.id if user else None,
                created_at=datetime.now(UTC),
            )
            self._store_archive(
                session, prompt, archive, meta, archive_name, replace=False
            )
            detail = self._detail(session, prompt)
            logging_service.log_audit_event(
                action="skill.import",
                resource_type="skill",
                resource_id=str(prompt.id),
                actor=user.username if user else None,
                skill_identifier=meta.identifier,
                file_count=len(archive.files),
                total_bytes=detail["total_bytes"],
            )
            return detail

    # -------------------------------------------------------------------- read

    def get_skill_detail(self, skill_id: int, user: User | None) -> dict[str, Any]:
        """Return a skill's metadata, sanitised instructions and file list."""
        with get_db_session() as session:
            prompt = self._load_skill(session, skill_id, user, "read")
            return self._detail(session, prompt)

    def get_file_preview(
        self, skill_id: int, path: str, user: User | None
    ) -> dict[str, Any]:
        """Return a text preview of one file (FR-016).

        Text is cut to ``SKILL_TEXT_PREVIEW_BYTES`` at a character boundary.
        Binary files return ``text=None`` and ``truncated=False``.
        """
        with get_db_session() as session:
            self._load_skill(session, skill_id, user, "read")
            file = SkillRepository(session).get_file(skill_id, path)
            if file is None:
                raise SkillLookupError(err.FILE_NOT_FOUND, "File not found")
            if not file.is_text:
                return {
                    "path": file.path,
                    "size": file.size,
                    "is_text": False,
                    "truncated": False,
                    "text": None,
                }
            limit = self._settings.text_preview_bytes
            content = bytes(file.content)
            text = content[:limit].decode("utf-8", errors="ignore")
            return {
                "path": file.path,
                "size": file.size,
                "is_text": True,
                "truncated": len(content) > limit,
                "text": text,
            }

    def get_file_raw(self, skill_id: int, path: str, user: User | None) -> RawFile:
        """Return the exact bytes of one stored file (FR-018)."""
        with get_db_session() as session:
            self._load_skill(session, skill_id, user, "read")
            file = SkillRepository(session).get_file(skill_id, path)
            if file is None:
                raise SkillLookupError(err.FILE_NOT_FOUND, "File not found")
            return RawFile(path=file.path, content=bytes(file.content))

    def export_skill(self, skill_id: int, user: User | None) -> SkillExport:
        """Build the standard-layout ``<identifier>.zip`` for a skill (FR-019).

        The archive is built per request from the stored bytes and never
        stored. Files are read one at a time and written straight into a
        spooled temporary file.
        """
        with get_db_session() as session:
            prompt = self._load_skill(session, skill_id, user, "read")
            repo = SkillRepository(session)
            package = repo.get_package(prompt.id)
            identifier = package.skill_identifier if package else "skill"
            stamp = package.files_updated_at if package else datetime.now(UTC)
            archive = write_skill_archive(
                identifier, repo.iter_file_contents(prompt.id), stamp
            )
        size = archive.seek(0, 2)
        archive.seek(0)
        return SkillExport(identifier=identifier, archive=archive, size=size)

    # ------------------------------------------------------------------ manage

    def update_skill_metadata(
        self, skill_id: int, request: Any, user: User | None
    ) -> dict[str, Any]:
        """Edit title, category, tags, note or favorite. Never creates a version.

        Args:
            skill_id: Skill id.
            request: A ``SkillUpdateRequest``; only fields present are applied.
            user: Acting user; must own the skill (administrators too).
        """
        fields = request.model_fields_set
        with get_db_session() as session:
            prompt = self._load_skill(session, skill_id, user, "write")
            if "title" in fields and request.title is not None:
                prompt.title = sanitize_text_field(
                    request.title, max_length=MAX_TITLE_LENGTH, allow_newlines=False
                )
            if "category" in fields:
                name = (
                    sanitize_text_field(
                        request.category,
                        max_length=MAX_CATEGORY_LENGTH,
                        allow_newlines=False,
                    )
                    if request.category
                    else ""
                )
                prompt.category_id = (
                    CategoryRepository(session).get_or_create(name).id if name else None
                )
            if "tags" in fields and request.tags is not None:
                prompt.tags = TagRepository(session).get_or_create_many(
                    split_tags(request.tags)
                )
            if "note" in fields and request.note is not None:
                prompt.note = sanitize_text_field(
                    request.note, max_length=MAX_NOTE_LENGTH, allow_newlines=True
                )
            if "favorite" in fields and request.favorite is not None:
                prompt.favorite = request.favorite
            prompt.updated_at = datetime.now(UTC)
            session.flush()
            session.refresh(prompt)
            return self._detail(session, prompt)

    def replace_skill_archive(
        self,
        skill_id: int,
        upload_bytes: bytes,
        archive_name: str,
        user: User | None,
    ) -> dict[str, Any]:
        """Replace a skill's files with a new archive (FR-022).

        The archive is read and checked before the database is touched, then
        the swap happens in one transaction: either every file is replaced or
        none is. Title, note, favorite, category and tags are kept; the
        description and identifier are refreshed from the new ``SKILL.md``.

        Raises:
            SkillLookupError: Unknown or not owned by the caller.
            SkillArchiveError: The archive was rejected (skill is unchanged).
        """
        with get_db_session() as session:
            self._load_skill(session, skill_id, user, "write")

        try:
            archive, meta, _ = self._read_and_parse(upload_bytes, archive_name)
        except SkillArchiveError as exc:
            self._audit_rejected(
                "skill.replace.rejected", archive_name, exc, user, skill_id
            )
            raise

        with get_db_session() as session:
            prompt = self._load_skill(session, skill_id, user, "write")
            self._store_archive(
                session, prompt, archive, meta, archive_name, replace=True
            )
            prompt.updated_at = datetime.now(UTC)
            session.flush()
            session.refresh(prompt)
            detail = self._detail(session, prompt)
            logging_service.log_audit_event(
                action="skill.replace",
                resource_type="skill",
                resource_id=str(prompt.id),
                actor=user.username if user else None,
                skill_identifier=meta.identifier,
                file_count=len(archive.files),
                total_bytes=detail["total_bytes"],
            )
            return detail

    def delete_skill(self, skill_id: int, user: User | None) -> None:
        """Delete a skill and, by cascade, its package and files (FR-023)."""
        with get_db_session() as session:
            prompt = self._load_skill(session, skill_id, user, "delete")
            audit_skill_deleted(prompt, actor=user.username if user else None)
            session.delete(prompt)
