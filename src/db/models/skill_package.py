# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""SkillPackage model: metadata of a skill stored as a ``prompts`` row.

A skill is a ``prompts`` row with ``item_type = 'skill'``. This table holds the
data only skills have (data-model.md); the files live in ``skill_files``.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.prompt import Prompt


class SkillPackage(Base):
    """One row per skill.

    Attributes:
        prompt_id: Primary key and foreign key to the parent ``prompts`` row.
        skill_identifier: Format-compliant slug used to name exports.
        description: Frontmatter ``description`` as written, or None.
        total_bytes: Sum of the sizes of the skill's files.
        file_count: Number of files in the skill.
        format_warnings: Warning codes recorded at import (empty = compliant).
        source_archive_name: File name of the most recent upload.
        files_updated_at: Time of the last import or replacement; also the
            fixed timestamp of export entries.
    """

    __tablename__ = "skill_packages"

    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"), primary_key=True
    )
    skill_identifier: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    format_warnings: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    source_archive_name: Mapped[str] = mapped_column(String(255), nullable=False)
    files_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    prompt: Mapped["Prompt"] = relationship("Prompt", back_populates="skill_package")

    def __repr__(self) -> str:
        return (
            f"<SkillPackage(prompt_id={self.prompt_id}, "
            f"identifier='{self.skill_identifier}', files={self.file_count})>"
        )
