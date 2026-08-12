# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from pathlib import Path

from src.services.logging_service import logging_service


def configure_logging(tmp_path: Path) -> Path:
    log_dir = tmp_path / "logs"
    logging_service.configure_logging(
        log_dir=str(log_dir), environment="test", force=True
    )
    return log_dir


def _read_audit_events(log_dir: Path):
    audit_file = log_dir / "audit.log"
    if not audit_file.exists():
        return []
    events = []
    for line in audit_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def test_prompt_creation_emits_audit_record(
    tmp_path, db_data_service, sample_prompt_data
):
    log_dir = configure_logging(tmp_path)

    prompt_id = db_data_service.add_new_prompt(sample_prompt_data(title="Audit Prompt"))

    events = _read_audit_events(log_dir)
    matching = [
        event
        for event in events
        if event.get("action") == "prompt.create"
        and event.get("resource_id") == str(prompt_id)
    ]
    assert matching, "Expected prompt.create audit log"
    entry = matching[-1]
    assert entry.get("title") == "Audit Prompt"
    assert entry.get("resource_type") == "prompt"


def test_backup_compression_emits_audit_record(tmp_path, db_backup_service):
    log_dir = configure_logging(tmp_path)

    backup_id = db_backup_service.create_backup("audit-backup")

    compressed = db_backup_service.compress_old_backups(days_threshold=0)

    assert compressed >= 1
    events = _read_audit_events(log_dir)
    compress_entries = [
        event for event in events if event.get("action") == "backup.compress"
    ]
    assert compress_entries, "Expected backup.compress audit log"
    creation_entries = [
        event
        for event in events
        if event.get("action") == "backup.create"
        and event.get("resource_id") == backup_id
    ]
    assert creation_entries, "Expected backup.create audit log"
