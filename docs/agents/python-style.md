# Python Conventions

- **Type hints** on all function signatures: `def get_prompt(self, prompt_id: int) -> Dict[str, Any]:`
- **Docstrings**: Google-style, on all classes and public methods, with Args/Returns/Raises.

  ```python
  def save_prompts(self) -> bool:
      """
      Save prompts to the data file.

      Returns:
          bool: True if successful, False otherwise
      """
  ```

- **Error handling**: wrap I/O and external calls in try/except; wrap DB operations in sessions with proper commit/rollback.
- **Naming**: `snake_case` for functions/methods/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- **Imports**: three groups — standard library, third-party, local application.
- **Service layer first**: business logic belongs in service classes, not web routes.
- **No hardcoded values**: use config/env vars/named constants.
- **No `print()`** in `src/` or `run_web.py` — use `logging_service.get_logger(__name__)`. Enforced by `make lint` (`rg "print\(" src run_web.py`).

## Logging & Observability

All code uses centralized structured logging (`logging_service.get_logger(__name__)`) with JSON payloads, request IDs, and rotating files in `data/logs/`. See [`docs/plan_centralized_error_logging.md`](../plan_centralized_error_logging.md) for mandated fields and retention targets.

- **Structured output**: `data/logs/app.log` and `data/logs/audit.log` emit JSON with `timestamp`, `level`, `event`, `request_id`, `actor`, `action`, `resource_id`, `status`, `duration_ms`. Never log prompt or note bodies — metadata only.
- **Request correlation**: every FastAPI request gets a request ID (UUIDv4 hex) propagated via `contextvars` into all services and included in every downstream log event.
- **Retention**: five 10 MB app log files (~2 weeks), ten 5 MB audit files (~30 days). `./data` is already a persisted volume; no extra volume needed.
- **Audit coverage**: prompt CRUD, version reverts, import/export actions, backup lifecycle events, cleanup/compression, and any automated intervention (e.g. auto-backups before deletes/imports) — actor identity + outcome (`success`/`failure`).
- **Config knobs**: `LOG_LEVEL`, `AUDIT_LOG_LEVEL` (default `INFO`), plus developer-friendly console formatting when `ENVIRONMENT=development`.
- Log write failures (ValidationMonitor, frontend error reports, logging subsystem itself) must go through the structured logger so they're alertable.

## Alembic Migrations

Migrations are authored/tested against **SQLite** in dev but run against **PostgreSQL** in production (see [`docs/DEPLOYMENT.md`](../DEPLOYMENT.md)). A migration that only works on one dialect passes local testing and breaks the production upgrade — this happened in `f1a2b3c4d5e6_enhanced_backup_tables` (fixed in v1.10.1).

- **Existence checks**: use `sa.inspect(conn).get_table_names()` / `.get_columns(table)`. Never query `sqlite_master` or `PRAGMA table_info(...)` directly — they don't exist on PostgreSQL.
- **Boolean defaults**: use `sa.true()` / `sa.false()` for `server_default` on Boolean columns. `sa.text("1")`/`sa.text("0")` works on SQLite but PostgreSQL rejects it as a type mismatch.
- **Column changes**: prefer `op.add_column`/`op.drop_column` (or `op.batch_alter_table` for SQLite table rebuilds) over raw `ALTER TABLE` strings, which tend to smuggle in dialect-specific types.
- **Before merging**: run the migration against a local PostgreSQL container in addition to SQLite dev — dev-only testing is exactly what let the above bug ship.
- Full command reference: [`docs/DEVELOPMENT.md#writing-alembic-migrations`](../DEVELOPMENT.md#writing-alembic-migrations).
