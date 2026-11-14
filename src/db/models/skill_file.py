# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""SkillFile model: one stored file of a skill package."""

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.prompt import Prompt


class SkillFile(Base):
    """One file of a skill, stored byte for byte.

    ``content`` is deferred: list and metadata queries never load it. It is read
    only for a single-file view, a download or an export.

    Attributes:
        id: Surrogate primary key.
        prompt_id: Parent skill (cascades on delete).
        path: Path relative to the skill root, ``/``-separated, NFC-normalised.
        path_folded: ``path.casefold()``; enforces case-insensitive uniqueness.
        size: Length of ``content`` in bytes.
        sha256: Lowercase hex digest of ``content``.
        is_text: True when the content has no NUL byte and is valid UTF-8.
        content: The exact bytes from the archive.
    """

    __tablename__ = "skill_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    path_folded: Mapped[str] = mapped_column(String(1024), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_text: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )
    content: Mapped[bytes] = deferred(mapped_column(LargeBinary, nullable=False))

    prompt: Mapped["Prompt"] = relationship("Prompt", back_populates="skill_files")

    __table_args__ = (
        UniqueConstraint("prompt_id", "path_folded", name="uq_skill_files_prompt_path"),
        Index("idx_skill_files_prompt", "prompt_id"),
    )

    def __repr__(self) -> str:
        return f"<SkillFile(prompt_id={self.prompt_id}, path='{self.path}')>"
