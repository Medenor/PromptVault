import json
import logging
from pathlib import Path

from src.services.logging_service import logging_service


def _flush_handlers() -> None:
    """Flush PromptVault logging handlers so file writes are available for assertions."""
    for name in ("promptvault", "promptvault.audit"):
        for handler in logging.getLogger(name).handlers:
            handler.flush()


def read_last_json_line(log_path: Path) -> dict:
    """Return the final JSON entry from the provided log file."""
    content = log_path.read_text(encoding="utf-8").strip().splitlines()
    return json.loads(content[-1])


def test_logging_service_emits_structured_app_logs(tmp_path):
    log_dir = tmp_path / "logs"
    logging_service.configure_logging(
        log_dir=str(log_dir), environment="test", force=True
    )
    logger = logging_service.get_logger("tests.logging")

    with logging_service.request_context(request_id="req-123", actor="tester"):
        logger.info(
            "Structured message",
            extra={
                "event": "tests.log",
                "resource_id": "unit",
                "status": 200,
                "duration_ms": 1.23,
            },
        )

    _flush_handlers()
    payload = read_last_json_line(log_dir / "app.log")

    assert payload["request_id"] == "req-123"
    assert payload["actor"] == "tester"
    assert payload["event"] == "tests.log"
    assert payload["status"] == 200
    assert payload["message"] == "Structured message"


def test_audit_logger_writes_separate_file(tmp_path):
    log_dir = tmp_path / "logs"
    logging_service.configure_logging(
        log_dir=str(log_dir), environment="test", force=True
    )
    audit_logger = logging_service.get_audit_logger()

    with logging_service.request_context(request_id="audit-req", actor="ops"):
        audit_logger.warning(
            "Backup restored",
            extra={
                "event": "backup.restore",
                "action": "restore_backup",
                "resource_id": "backup-123",
                "status": "success",
            },
        )

    _flush_handlers()
    payload = read_last_json_line(log_dir / "audit.log")

    assert payload["request_id"] == "audit-req"
    assert payload["actor"] == "ops"
    assert payload["resource_id"] == "backup-123"
    assert payload["logger"] == "promptvault.audit"


def test_generate_request_id_returns_hex():
    request_id = logging_service.generate_request_id()
    assert len(request_id) == 32
    int(request_id, 16)  # Should not raise
