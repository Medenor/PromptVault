# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Hardened skill archive reader: malicious fixtures, clutter, root detection."""

import hashlib
import io
import zipfile

import pytest
from fixtures.skills import build_fixtures as bf

from src.config.skill_config import SkillSettings
from src.services.skills import errors as err
from src.services.skills.archive_reader import (
    ArchiveFile,
    SkillArchiveReader,
    _Entry,
    _read_member,
)
from src.services.skills.errors import SkillArchiveError


@pytest.fixture
def reader() -> SkillArchiveReader:
    return SkillArchiveReader(SkillSettings())


@pytest.mark.parametrize("case", bf.REJECTED_CASES, ids=lambda c: c.id)
def test_rejects_every_malicious_fixture(reader, case):
    with pytest.raises(SkillArchiveError) as excinfo:
        reader.read(case.build(), "skill.zip")
    assert excinfo.value.code == case.code
    if case.offending_entry is not None:
        assert excinfo.value.offending_entry == case.offending_entry


def test_rejects_empty_bytes(reader):
    with pytest.raises(SkillArchiveError) as excinfo:
        reader.read(b"", "skill.zip")
    assert excinfo.value.code == err.ARCHIVE_INVALID


def test_wrapped_archive_strips_folder_and_drops_empty_folders(
    reader, skill_zip_valid_wrapped
):
    result = reader.read(skill_zip_valid_wrapped, "pdf-tools.zip")
    assert result.has_wrapping_folder is True
    assert result.wrapped_folder_name == "pdf-tools"
    assert sorted(f.path for f in result.files) == [
        "SKILL.md",
        "references/sample.bin",
        "scripts/fill.py",
    ]
    assert all("pdf-tools" not in f.path for f in result.files)


def test_root_level_archive_has_no_wrapping_folder(reader, skill_zip_valid_root):
    result = reader.read(skill_zip_valid_root, "x.zip")
    assert result.has_wrapping_folder is False
    assert result.wrapped_folder_name is None
    assert {f.path for f in result.files} == {"SKILL.md", "scripts/fill.py"}


def test_files_carry_exact_bytes_hash_and_text_flag(reader, skill_zip_valid_wrapped):
    files = {f.path: f for f in reader.read(skill_zip_valid_wrapped, "x.zip").files}
    binary = files["references/sample.bin"]
    assert binary.content == bf.BINARY_SAMPLE
    assert binary.size == len(bf.BINARY_SAMPLE)
    assert binary.sha256 == hashlib.sha256(bf.BINARY_SAMPLE).hexdigest()
    assert binary.is_text is False
    assert files["SKILL.md"].is_text is True
    assert files["SKILL.md"].content == bf.SKILL_MD_VALID.encode()


def test_clutter_is_skipped_and_not_counted(skill_zip_with_clutter):
    reader = SkillArchiveReader(SkillSettings(max_files=1))
    result = reader.read(skill_zip_with_clutter, "x.zip")
    assert [f.path for f in result.files] == ["SKILL.md"]


def test_dot_segments_are_dropped_not_rejected(reader, make_skill_zip):
    data = make_skill_zip([("./SKILL.md", bf.SKILL_MD_VALID), ("./a/./b.txt", "x")])
    result = reader.read(data, "x.zip")
    assert {f.path for f in result.files} == {"SKILL.md", "a/b.txt"}


def test_backslash_separators_are_normalised(reader, make_skill_zip):
    data = make_skill_zip([("SKILL.md", bf.SKILL_MD_VALID), ("docs\\guide.md", "x")])
    result = reader.read(data, "x.zip")
    assert "docs/guide.md" in {f.path for f in result.files}


def test_backslash_traversal_is_rejected(reader, make_skill_zip):
    data = make_skill_zip([("SKILL.md", bf.SKILL_MD_VALID), ("..\\evil.txt", "x")])
    with pytest.raises(SkillArchiveError) as excinfo:
        reader.read(data, "x.zip")
    assert excinfo.value.code == err.ENTRY_PATH_UNSAFE


def test_paths_are_nfc_normalised(reader, make_skill_zip):
    decomposed = "cafe\u0301.md"  # e + combining acute
    data = make_skill_zip([("SKILL.md", bf.SKILL_MD_VALID), (decomposed, "x")])
    paths = {f.path for f in reader.read(data, "x.zip").files}
    assert "caf\u00e9.md" in paths


def test_nfc_duplicates_are_detected(reader, make_skill_zip):
    data = make_skill_zip(
        [("SKILL.md", bf.SKILL_MD_VALID), ("caf\u00e9.md", "a"), ("cafe\u0301.md", "b")]
    )
    with pytest.raises(SkillArchiveError) as excinfo:
        reader.read(data, "x.zip")
    assert excinfo.value.code == err.ENTRY_DUPLICATE


def test_depth_at_the_limit_is_accepted(reader):
    result = reader.read(bf.too_deep(levels=10), "x.zip")
    assert len(result.files) == 2


def test_file_count_at_the_limit_is_accepted():
    reader = SkillArchiveReader(SkillSettings(max_files=5))
    result = reader.read(bf.too_many_files(count=5), "x.zip")
    assert len(result.files) == 5


def test_configurable_limits_are_honoured(skill_zip_valid_wrapped):
    reader = SkillArchiveReader(SkillSettings(max_file_bytes=1000))
    with pytest.raises(SkillArchiveError) as excinfo:
        reader.read(skill_zip_valid_wrapped, "x.zip")
    assert excinfo.value.code == err.LIMIT_FILE_SIZE
    assert excinfo.value.offending_entry == "pdf-tools/references/sample.bin"


def test_depth_is_measured_from_the_skill_root(make_skill_zip):
    deep = "/".join(f"d{i}" for i in range(3)) + "/leaf.txt"
    data = make_skill_zip([("wrap/SKILL.md", bf.SKILL_MD_VALID), (f"wrap/{deep}", "x")])
    SkillArchiveReader(SkillSettings(max_depth=3)).read(data, "x.zip")
    with pytest.raises(SkillArchiveError) as excinfo:
        SkillArchiveReader(SkillSettings(max_depth=2)).read(data, "x.zip")
    assert excinfo.value.code == err.LIMIT_DEPTH


def test_nested_skill_md_does_not_count_as_root(reader, make_skill_zip):
    data = make_skill_zip([("a/b/SKILL.md", bf.SKILL_MD_VALID), ("a/c.txt", "x")])
    with pytest.raises(SkillArchiveError) as excinfo:
        reader.read(data, "x.zip")
    assert excinfo.value.code == err.SKILL_MD_MISSING


def test_skill_md_limit_applies_only_to_the_root_skill_md(make_skill_zip):
    data = make_skill_zip(
        [("SKILL.md", bf.SKILL_MD_VALID), ("docs/SKILL.md", "x" * 5000)]
    )
    result = SkillArchiveReader(SkillSettings(max_skill_md_bytes=1000)).read(
        data, "x.zip"
    )
    assert len(result.files) == 2


def test_rejection_error_serialises_to_the_contract_body():
    error = SkillArchiveError(err.ENTRY_LINK, "nope", "link")
    assert error.to_detail() == {
        "code": "ENTRY_LINK",
        "message": "nope",
        "offending_entry": "link",
    }
    assert error.http_status == 400
    assert SkillArchiveError(err.LIMIT_UPLOAD_SIZE, "big").http_status == 413


def _fake_member(stream: bytes, compress_size: int = 10):
    info = zipfile.ZipInfo("big.bin")
    info.compress_size = compress_size
    info.file_size = 1  # the header lies about its size

    class _Zip:
        def open(self, _info):
            return io.BytesIO(stream)

    return _Zip(), _Entry(info=info, parts=["big.bin"])


def test_live_count_catches_a_header_that_lies_about_size():
    zf, entry = _fake_member(b"a" * 5000)
    settings = SkillSettings(max_file_bytes=1000)
    with pytest.raises(SkillArchiveError) as excinfo:
        _read_member(zf, entry, "big.bin", 0, settings)
    assert excinfo.value.code == err.LIMIT_FILE_SIZE


def test_live_count_enforces_the_running_total():
    zf, entry = _fake_member(b"a" * 600)
    settings = SkillSettings(max_total_bytes=1000)
    with pytest.raises(SkillArchiveError) as excinfo:
        _read_member(zf, entry, "big.bin", 500, settings)
    assert excinfo.value.code == err.LIMIT_TOTAL_SIZE


def test_live_count_enforces_the_skill_md_limit():
    zf, entry = _fake_member(b"a" * 5000)
    settings = SkillSettings(max_skill_md_bytes=1000)
    with pytest.raises(SkillArchiveError) as excinfo:
        _read_member(zf, entry, "SKILL.md", 0, settings)
    assert excinfo.value.code == err.LIMIT_SKILL_MD_SIZE


def test_live_ratio_check_catches_a_header_that_lies_about_compressed_size():
    zf, entry = _fake_member(b"0" * (2 * 1024 * 1024), compress_size=100)
    with pytest.raises(SkillArchiveError) as excinfo:
        _read_member(zf, entry, "big.bin", 0, SkillSettings())
    assert excinfo.value.code == err.ARCHIVE_SUSPICIOUS_RATIO


def test_corrupt_member_data_is_reported_as_invalid(reader):
    data = bytearray(bf.build_zip([("SKILL.md", "hello world" * 50)]))
    offset = data.find(b"SKILL.md") + len(b"SKILL.md")
    for i in range(offset, offset + 20):
        data[i] ^= 0xFF  # damage the compressed stream
    with pytest.raises(SkillArchiveError) as excinfo:
        reader.read(bytes(data), "x.zip")
    assert excinfo.value.code == err.ARCHIVE_INVALID


def test_read_returns_archive_file_dataclass(reader, skill_zip_valid_root):
    first = reader.read(skill_zip_valid_root, "x.zip").files[0]
    assert isinstance(first, ArchiveFile)
