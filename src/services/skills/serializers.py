# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Plain-dict serialisation of skills, shared by the list and detail paths.

Kept free of web-layer imports so the service and the prompt routers can both
use it. The shapes match ``SkillSummary`` and ``SkillDetail`` in
contracts/skills-api.md.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.db.models import Prompt, SkillFile, SkillPackage


def skill_summary_dict(
    prompt: "Prompt", package: "SkillPackage | None"
) -> dict[str, Any]:
    """Build the ``SkillSummary`` dict for a skill row (no ``prompt`` body).

    Args:
        prompt: The ``prompts`` row (``item_type='skill'``).
        package: Its ``skill_packages`` row, or None if missing.

    Returns:
        dict: Summary fields; deliberately omits the ``SKILL.md`` text.
    """
    return {
        "id": prompt.id,
        "item_type": "skill",
        "title": prompt.title,
        "skill_identifier": package.skill_identifier if package else "",
        "description": package.description if package else None,
        "category": prompt.category.name if prompt.category else "",
        "category_color": prompt.category.color if prompt.category else None,
        "tags": [tag.name for tag in prompt.tags] if prompt.tags else [],
        "tag_colors": (
            {tag.name: tag.color for tag in prompt.tags} if prompt.tags else {}
        ),
        "favorite": prompt.favorite,
        "file_count": package.file_count if package else 0,
        "total_bytes": package.total_bytes if package else 0,
        "format_warnings": list(package.format_warnings) if package else [],
        "user_id": prompt.user_id,
        "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
        "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
    }


def skill_file_entry(file: "SkillFile") -> dict[str, Any]:
    """Build one ``SkillFileEntry`` (metadata only, never the content)."""
    return {
        "path": file.path,
        "size": file.size,
        "is_text": bool(file.is_text),
        "sha256": file.sha256,
    }
