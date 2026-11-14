# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Lenient SKILL.md frontmatter parsing, warning codes and identifier slugs."""

import pytest

from src.services.skills import frontmatter as fm


def parse(text: str | bytes, folder: str | None = "pdf-tools", archive="x.zip"):
    raw = text if isinstance(text, bytes) else text.encode("utf-8")
    return fm.parse_skill_md(raw, folder, archive)


GOOD = "---\nname: pdf-tools\ndescription: Fill forms.\n---\nBody\n"


def test_fully_compliant_skill_has_no_warnings():
    meta = parse(GOOD)
    assert meta.warnings == []
    assert meta.name == "pdf-tools"
    assert meta.description == "Fill forms."
    assert meta.identifier == "pdf-tools"
    assert meta.title == "pdf-tools"
    assert meta.text == GOOD


def test_unknown_frontmatter_fields_and_placeholders_are_preserved():
    text = (
        "---\nname: a\ndescription: b\nlicense: MIT\nmetadata:\n  k: [1, 2]\n---\n"
        "Use ${CLAUDE_SKILL_DIR}/x.sh\n"
    )
    meta = parse(text, folder="a")
    assert meta.warnings == []
    assert meta.text == text


def test_frontmatter_missing():
    meta = parse("# Title\nNo frontmatter\n", folder=None, archive="my-skill.zip")
    assert meta.warnings == [fm.FRONTMATTER_MISSING, fm.NO_WRAPPING_FOLDER]
    assert meta.title == "my-skill"
    assert meta.identifier == "my-skill"
    assert meta.name is None


@pytest.mark.parametrize(
    "text",
    [
        "---\nname: [unclosed\n---\nbody",
        "---\nname: a\n",  # never closed
        "---\n- just\n- a list\n---\nbody",
        "---\njust a scalar\n---\nbody",
        "---\nname: !!python/object/apply:os.system ['echo hi']\n---\nbody",
    ],
)
def test_frontmatter_malformed(text):
    meta = parse(text)
    assert meta.warnings == [fm.FRONTMATTER_MALFORMED]


def test_safe_load_refuses_python_object_tags_without_executing():
    marker = "---\nx: !!python/object/apply:builtins.exit []\n---\n"
    meta = parse(marker)  # would raise SystemExit if it were executed
    assert fm.FRONTMATTER_MALFORMED in meta.warnings


def test_frontmatter_over_64_kb_is_malformed():
    big = (
        "---\nname: a\ndescription: " + "x" * (fm.MAX_FRONTMATTER_BYTES + 1) + "\n---\n"
    )
    assert parse(big, folder="a").warnings == [fm.FRONTMATTER_MALFORMED]


def test_frontmatter_nesting_over_20_levels_is_malformed():
    nested = "x"
    for _ in range(fm.MAX_FRONTMATTER_DEPTH + 2):
        nested = f"[{nested}]"
    text = f"---\nname: a\ndescription: b\ndeep: {nested}\n---\n"
    assert parse(text, folder="a").warnings == [fm.FRONTMATTER_MALFORMED]


def test_alias_bombs_do_not_blow_up_depth_computation():
    lines = ["---", "a: &a [x, x, x, x, x, x, x, x, x]"]
    previous = "a"
    for i in range(1, 12):
        name = chr(ord("a") + i)
        lines.append(
            f"{name}: &{name} [*{previous}, *{previous}, *{previous}, *{previous}]"
        )
        previous = name
    lines.append("---")
    meta = parse("\n".join(lines))
    assert fm.FRONTMATTER_MALFORMED in meta.warnings or meta.warnings  # finishes


def test_name_missing_and_description_missing():
    meta = parse(
        "---\nlicense: MIT\n---\nbody", folder="pdf-tools", archive="Cool Skill.zip"
    )
    assert meta.warnings == [fm.NAME_MISSING, fm.DESCRIPTION_MISSING]
    assert meta.title == "Cool Skill"
    assert meta.identifier == "cool-skill"


def test_blank_name_and_description_count_as_missing():
    meta = parse('---\nname: "  "\ndescription: ""\n---\nbody')
    assert meta.warnings == [fm.NAME_MISSING, fm.DESCRIPTION_MISSING]


@pytest.mark.parametrize(
    "name", ["Bad Name", "UPPER", "under_score", "-lead", "trail-", "a--b"]
)
def test_name_invalid(name):
    meta = parse(f"---\nname: {name!r}\ndescription: d\n---\nbody", folder=name)
    assert fm.NAME_INVALID in meta.warnings
    assert meta.title == name


def test_name_with_a_trailing_newline_is_invalid():
    # "$" would accept "foo\n"; the identifier ends up in headers and zip names.
    meta = parse('---\nname: "foo\\n"\ndescription: d\n---\nbody', folder="foo")
    assert fm.NAME_INVALID in meta.warnings
    assert "\n" not in meta.identifier


def test_name_over_64_characters_is_invalid():
    name = "a" * 65
    meta = parse(f"---\nname: {name}\ndescription: d\n---\n", folder=name)
    assert fm.NAME_INVALID in meta.warnings
    assert len(meta.identifier) == 64


def test_name_folder_mismatch():
    meta = parse(GOOD, folder="other-folder")
    assert meta.warnings == [fm.NAME_FOLDER_MISMATCH]
    assert meta.identifier == "pdf-tools"


def test_no_mismatch_check_without_a_wrapping_folder():
    assert parse(GOOD, folder=None).warnings == [fm.NO_WRAPPING_FOLDER]


def test_description_too_long_is_kept_as_written():
    long_description = "d" * 1025
    meta = parse(f"---\nname: a\ndescription: {long_description}\n---\n", folder="a")
    assert meta.warnings == [fm.DESCRIPTION_TOO_LONG]
    assert meta.description == long_description


def test_description_exactly_1024_is_fine():
    meta = parse(f"---\nname: a\ndescription: {'d' * 1024}\n---\n", folder="a")
    assert meta.warnings == []


def test_scalar_description_is_coerced_and_container_is_missing():
    assert parse("---\nname: a\ndescription: 42\n---\n", folder="a").description == "42"
    meta = parse("---\nname: a\ndescription: [x]\n---\n", folder="a")
    assert meta.warnings == [fm.DESCRIPTION_MISSING]


def test_byte_order_mark_is_removed_from_text():
    meta = parse(b"\xef\xbb\xbf" + GOOD.encode())
    assert meta.warnings == []
    assert meta.text == GOOD


def test_non_utf8_skill_md_warns_and_decodes_with_replacement():
    meta = parse(b"---\nname: pdf-tools\ndescription: d\n---\n\xff\xfe bad")
    assert meta.warnings == [fm.SKILL_MD_NOT_UTF8]
    assert "\ufffd" in meta.text


def test_crlf_frontmatter_is_recognised():
    text = "---\r\nname: pdf-tools\r\ndescription: d\r\n---\r\nbody\r\n"
    assert parse(text).warnings == []


def test_warning_order_is_stable():
    meta = parse(b"---\nname: Bad\n---\n\xff", folder=None)
    assert meta.warnings == [
        fm.NAME_INVALID,
        fm.DESCRIPTION_MISSING,
        fm.NO_WRAPPING_FOLDER,
        fm.SKILL_MD_NOT_UTF8,
    ]


def test_title_is_cut_to_200_characters():
    meta = parse(f"---\nname: {'a' * 300}\ndescription: d\n---\n", folder=None)
    assert len(meta.title) == fm.MAX_TITLE_LENGTH


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("PDF Tools!", "pdf-tools"),
        ("Café Résumé", "cafe-resume"),
        ("日本語", "skill"),
        ("", "skill"),
        (None, "skill"),
        ("---", "skill"),
        ("a" * 70, "a" * 64),
        ("a" * 63 + " b", "a" * 63),
        ("  Hello___World  ", "hello-world"),
    ],
)
def test_slugify(value, expected):
    assert fm.slugify(value) == expected
    assert fm.NAME_PATTERN.match(fm.slugify(value))


def test_archive_stem_strips_directories_and_zip_suffix():
    assert fm.archive_stem("C:\\tmp\\My Skill.ZIP") == "My Skill"
    assert fm.archive_stem("dir/skill.zip") == "skill"
    assert fm.archive_stem("plain") == "plain"


def test_strip_frontmatter_only_removes_a_closed_block():
    assert fm.strip_frontmatter(GOOD) == "Body\n"
    unclosed = "---\nname: a\nbody"
    assert fm.strip_frontmatter(unclosed) == unclosed
    assert fm.strip_frontmatter("no front") == "no front"


def test_empty_archive_name_falls_back_to_default():
    meta = parse("# x", folder=None, archive=".zip")
    assert meta.identifier == "skill"
    assert meta.title == "skill"
