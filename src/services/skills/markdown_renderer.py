# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Server-side rendering of ``SKILL.md`` instructions (research.md Decision 6).

Two independent layers keep the output inert: ``markdown-it-py`` runs with raw
HTML disabled (and its default link validation), then ``nh3`` sanitises the
result against an explicit allow-list.
"""

import nh3
from markdown_it import MarkdownIt

from src.services.skills.frontmatter import strip_frontmatter

_ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "del",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "code": {"class"},
    "th": {"align"},
    "td": {"align"},
}
_ALLOWED_SCHEMES = {"http", "https", "mailto"}

_RENDERER = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])


def render_instructions(skill_md_text: str) -> str:
    """Render the body of a ``SKILL.md`` to sanitised HTML.

    Args:
        skill_md_text: Full ``SKILL.md`` text; frontmatter is removed first.

    Returns:
        str: HTML containing only allow-listed tags. Links open safely
        (``rel="noopener noreferrer nofollow"``) and unsafe URL schemes are
        dropped.
    """
    body = strip_frontmatter(skill_md_text)
    html = _RENDERER.render(body)
    return nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_SCHEMES,
        link_rel="noopener noreferrer nofollow",
        strip_comments=True,
    )
