# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""SKILL.md rendering: frontmatter removed, nothing active survives."""

import pytest

from src.services.skills.markdown_renderer import render_instructions

FRONT = "---\nname: x\ndescription: y\n---\n"


def test_frontmatter_is_removed():
    html = render_instructions(FRONT + "# Heading\n")
    assert "<h1>Heading</h1>" in html
    assert "name: x" not in html and "description" not in html


def test_headings_lists_code_and_links_survive():
    md = (
        "# T\n\n## S\n\n- one\n- two\n\n1. a\n2. b\n\n"
        "```python\nprint(1)\n```\n\n`inline`\n\n[site](https://example.com)\n"
    )
    html = render_instructions(md)
    for fragment in (
        "<h1>T</h1>",
        "<h2>S</h2>",
        "<ul>",
        "<ol>",
        "<li>one</li>",
        "<pre>",
        "<code",
    ):
        assert fragment in html
    assert 'href="https://example.com"' in html
    assert 'rel="noopener noreferrer nofollow"' in html


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<iframe src='https://evil.example'></iframe>",
        "<div onclick='x()'>hi</div>",
        "<style>body{display:none}</style>",
        "<svg onload=alert(1)>",
        "<a href='javascript:alert(1)'>x</a>",
    ],
)
def test_raw_html_never_becomes_active_markup(payload):
    html = render_instructions(FRONT + payload + "\n")
    assert "<script" not in html
    assert "<img" not in html
    assert "<iframe" not in html
    assert "<style" not in html
    assert "<svg" not in html
    assert "<div" not in html
    assert "onerror=" not in html.replace("&lt;", "") or "&lt;" in html


def test_raw_html_block_is_shown_as_escaped_text():
    html = render_instructions("<script>alert(1)</script>\n")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


@pytest.mark.parametrize(
    "link",
    [
        "[x](javascript:alert(1))",
        "[x](JaVaScRiPt:alert(1))",
        "[x](data:text/html;base64,PHNjcmlwdD4=)",
        "[x](vbscript:msgbox(1))",
    ],
)
def test_dangerous_link_schemes_are_not_linked(link):
    html = render_instructions(link + "\n")
    assert "<a " not in html
    assert "href" not in html


def test_images_are_not_rendered_as_elements():
    html = render_instructions("![alt](https://example.com/a.png)\n")
    assert "<img" not in html


def test_tool_placeholders_stay_literal():
    html = render_instructions("Run ${CLAUDE_SKILL_DIR}/scripts/x.sh\n")
    assert "${CLAUDE_SKILL_DIR}/scripts/x.sh" in html


def test_tables_and_strikethrough_are_supported():
    html = render_instructions("| a | b |\n|---|---|\n| 1 | 2 |\n\n~~gone~~\n")
    assert "<table>" in html and "<s>gone</s>" in html


def test_html_comments_are_stripped():
    html = render_instructions("text <!-- secret --> more\n")
    assert "secret" not in html or "&lt;!--" in html


def test_empty_input_renders_empty():
    assert render_instructions("").strip() == ""
