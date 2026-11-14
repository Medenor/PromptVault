# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Skill export archive: layout, determinism, round trip, reference validator."""

import hashlib
import io
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime

import pytest
from fixtures.skills import build_fixtures as bf

from src.config.skill_config import SkillSettings
from src.services.skills.archive_reader import SkillArchiveReader
from src.services.skills.archive_writer import write_skill_archive
from src.services.skills.frontmatter import parse_skill_md

STAMP = datetime(2026, 11, 13, 10, 30, 41, tzinfo=UTC)


def _files(reader_result):
    return [(f.path, f.content) for f in reader_result.files]


def _archive_bytes(identifier, files, stamp=STAMP) -> bytes:
    spool = write_skill_archive(identifier, files, stamp)
    try:
        return spool.read()
    finally:
        spool.close()


@pytest.fixture
def stored_files(skill_zip_valid_wrapped):
    return _files(
        SkillArchiveReader(SkillSettings()).read(skill_zip_valid_wrapped, "x.zip")
    )


def test_entries_are_prefixed_with_the_identifier(stored_files):
    data = _archive_bytes("pdf-tools", stored_files)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
    assert names and all(n.startswith("pdf-tools/") for n in names)
    assert "pdf-tools/SKILL.md" in names


def test_same_input_produces_identical_bytes(stored_files):
    assert _archive_bytes("pdf-tools", stored_files) == _archive_bytes(
        "pdf-tools", stored_files
    )


def test_every_file_matches_by_sha256(stored_files):
    data = _archive_bytes("pdf-tools", stored_files)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for path, content in stored_files:
            written = zf.read(f"pdf-tools/{path}")
            assert hashlib.sha256(written).digest() == hashlib.sha256(content).digest()


def test_round_trip_through_the_reader_is_lossless_and_warning_free(stored_files):
    data = _archive_bytes("pdf-tools", stored_files)
    result = SkillArchiveReader(SkillSettings()).read(data, "pdf-tools.zip")
    assert result.has_wrapping_folder and result.wrapped_folder_name == "pdf-tools"
    assert sorted(_files(result)) == sorted(stored_files)
    skill_md = next(c for p, c in _files(result) if p == "SKILL.md")
    assert (
        parse_skill_md(skill_md, result.wrapped_folder_name, "pdf-tools.zip").warnings
        == []
    )


def test_pre_1980_timestamp_is_clamped(stored_files):
    data = _archive_bytes("x", stored_files, datetime(1970, 1, 1, tzinfo=UTC))
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert zf.infolist()[0].date_time[0] == 1980


def test_odd_seconds_are_rounded_down_to_zip_resolution(stored_files):
    data = _archive_bytes("x", stored_files)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert zf.infolist()[0].date_time == (2026, 11, 13, 10, 30, 40)


def test_large_archives_spill_to_disk_and_stay_readable():
    big = [
        ("SKILL.md", bf.SKILL_MD_VALID.encode()),
        ("big.bin", bytes(range(256)) * 50_000),
    ]
    spool = write_skill_archive("big", big, STAMP)
    try:
        spool.seek(0)
        with zipfile.ZipFile(spool) as zf:
            assert len(zf.read("big/big.bin")) == 256 * 50_000
    finally:
        spool.close()


@pytest.mark.skipif(shutil.which("skills-ref") is None, reason="skills-ref not on PATH")
def test_exported_archive_passes_the_reference_validator(stored_files, tmp_path):
    """SC-008: a warning-free export is accepted by ``skills-ref validate``."""
    data = _archive_bytes("pdf-tools", stored_files)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(tmp_path)  # test-only: trusted bytes written by our own writer
    proc = subprocess.run(
        ["skills-ref", "validate", str(tmp_path / "pdf-tools")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
