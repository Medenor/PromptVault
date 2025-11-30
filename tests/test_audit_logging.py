# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import json
from pathlib import Path

from src.services.logging_service import logging_service
from src.services.prompt_data_service import PromptDataService
from src.services.backup_service import BackupService


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


def test_prompt_creation_emits_audit_record(tmp_path):
    log_dir = configure_logging(tmp_path)
    data_file = tmp_path / "prompts.json"
    service = PromptDataService(str(data_file))

    prompt_id = service.create_prompt({"title": "Audit Prompt", "prompt": "Body"})

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


def test_backup_compression_emits_audit_record(tmp_path):
    log_dir = configure_logging(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    data_file = data_dir / "prompts_data.json"
    data_file.write_text(json.dumps({"next_id": 1, "prompts": {}}), encoding="utf-8")

    service = BackupService(str(data_dir))
    backup_id = service.create_backup("audit-backup")

    compressed = service.compress_old_backups(days_threshold=0)

    assert compressed == 1
    events = _read_audit_events(log_dir)
    compress_entries = [
        event for event in events if event.get("action") == "backup.compress"
    ]
    assert compress_entries, "Expected backup.compress audit log"
    assert compress_entries[-1].get("compressed_count") == 1
    creation_entries = [
        event
        for event in events
        if event.get("action") == "backup.create"
        and event.get("resource_id") == backup_id
    ]
    assert creation_entries, "Expected backup.create audit log"
