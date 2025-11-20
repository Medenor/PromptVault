# Centralized Error Handling & Structured Logging Plan (Issue #10)

This document breaks the work into phased checklists so the team can implement centralized logging, auditing, and error handling while continuously refining the plan after each phase.

## Phase 1 – Baseline Assessment & Requirements Validation
- [x] Catalog every `print()`-based log, bare `except`, and unlogged side effect in `src/services`, `src/web/app.py`, and `run_web.py` to quantify current coverage gaps.
- [x] Interview stakeholders (ops/maintainers) to lock down observability goals (retention, log rotation, required metadata, privacy limits) and update AGENTS.md requirements section accordingly.
- [x] Assess infrastructure constraints: available disk in `data/logs/`, backup interactions, and whether the Docker image needs extra volumes for log shipping.
- [x] Define success metrics for this initiative (e.g., 100% of API routes emit structured request logs, 0 uncaught exceptions logged only to stdout) and capture them in ROADMAP.md / issue #10 comments.
- [x] Implementation plan refinement for Phase 2 summarizing discoveries (coverage gaps, infra constraints, metrics) so the logging design directly reflects Phase 1 learnings.

### Phase 1 Findings

#### Print Statement Inventory (`src` + `run_web.py`)

- `src/services/prompt_data_service.py`
  - L148 `print(f"Save Error: Could not save prompts: {e}")`
  - L151 `print(f"Unknown Save Error: An unexpected error occurred while saving: {e}")`
  - L193 `print(f"Warning: Invalid structure for prompt ID '{k}', ignored.")`
  - L197 `print(f"Warning: Invalid prompt key '{k}', ignored.")`
  - L233 `print(f"Load Error: Could not load prompts from {self.data_file}: {e}")`
  - L240 `print(f"Unknown Error: An unexpected error occurred while loading: {e}")`
  - L264 `print(f"Migrating old prompt structure for ID {prompt_id}")`
  - L555 `print(f"Error clearing all prompts: {e}")`
- `src/services/prompt_import_export_service.py`
  - L45 `print(f"Export Error: Failed to export prompts to CSV: {e}")`
  - L81 `print(f"Export Error: Failed to export prompts to Markdown: {e}")`
  - L131 `print(f"Import Warning: Skipping malformed CSV row: {row_error}")`
  - L136 `print(f"Import Error: Failed to import prompts from CSV: {e}")`
  - L216 `print(f"Import Error: Failed to import prompts from Markdown: {e}")`
- `src/services/backup_service.py`
  - L48 `print(f"Backup Error: Data file {self.data_file} does not exist")`
  - L96 `print(f"Backup created successfully: {backup_filename}")`
  - L100 `print(f"Backup Error: Failed to create backup: {e}")`
  - L122 `print(f"Warning: Could not read backup metadata {filename}: {e}")`
  - L130 `print(f"Error listing backups: {e}")`
  - L147 `print(f"Restore Error: Backup file for ID {backup_id} does not exist")`
  - L151 `print(f"Restore Error: Backup {backup_id} appears to be corrupted")`
  - L155 `print("Creating pre-restore backup...")`
  - L158 `print("Warning: Could not create pre-restore backup")`
  - L169 `print(f"Backup {backup_id} restored successfully")`
  - L173 `print(f"Restore Error: Failed to restore backup {backup_id}: {e}")`
  - L212 `print(f"Removed old backup: {backup_filename}")`
  - L214 `print(f"Warning: Could not remove backup {backup_filename}: {e}")`
  - L219 `print(f"Cleanup completed: {removed_count} old backups removed")`
  - L222 `print(f"Cleanup Error: Failed to cleanup old backups: {e}")`
  - L292 `print(f"Compressed backup: {backup_filename}")`
  - L295 `print(f"Warning: Could not compress backup {backup_filename}: {e}")`
  - L300 `print(f"Compression completed: {compressed_count} backups compressed")`
  - L303 `print(f"Compression Error: Failed to compress old backups: {e}")`
  - L377 `print(f"Delete Error: Failed to delete backup {backup_id}: {e}")`
  - L439 `print(f"Backup Validation Error: {e}")`
- `src/web/monitoring/validation_monitor.py`
  - L54 `print(f"[ValidationMonitor] Failed to load metrics: {exc}")`
  - L63 `print(f"[ValidationMonitor] Failed to write metrics: {exc}")`
- `src/web/app.py`
  - L134 `print(f"[ValidationMonitor] Unable to record event for {endpoint}: {exc}")`
  - L534 `print(f"Automatic backup created before deleting prompt {prompt_id}: {backup_id}")`
  - L802 `print(f"Automatic backup created before replace import: {backup_id}")`
- `run_web.py` currently has no `print()` statements.

#### Bare `except` Blocks

- No bare `except:` clauses exist in `src/services`, `src/web`, or `run_web.py`. All exception handlers specify an exception class (mostly `Exception`) but still need refactoring into structured logging and typed exceptions.

#### High-Risk Unlogged Side Effects

- `PromptDataService`: `create_prompt`, `update_prompt`, `delete_prompt`, `clear_all_prompts`, migration logic, and file writes run silently on success; load/save calls only report failures.
- `PromptVersioningService`: All version creation/revert helpers mutate prompt history without emitting any trace, making it impossible to follow version trees.
- `PromptImportExportService`: Successful exports/imports, deduplication, and validation skips are not logged, hindering user-facing audits.
- `BackupService`: Success paths (backup creation, cleanup, compression) rely on `print()` but do not capture structured metadata such as requester or duration; disk pruning happens without durable logs.
- `FastAPI` routes in `src/web/app.py`: create/update/delete/import/export endpoints lack any request logging aside from the two auto-backup prints, so there is no trail of who performed an operation.
- `ValidationMonitor`: writes metrics to `data/logs/validation_metrics.json` but only prints errors, giving no persistent evidence of monitor health.

### Observability Requirements Confirmed with Maintainer Guidance

- Structured JSON logs must be written for both application flow (`data/logs/app.log`) and high-value events (`data/logs/audit.log`). Every entry needs `timestamp`, `level`, `event`, `request_id`, `actor`, `action`, `target_id` (`prompt_id`, `backup_id`, etc.), and `duration_ms`.
- Request IDs must be generated per HTTP request (FastAPI middleware + `contextvars`) and propagated down into service calls so audit entries can be correlated end-to-end.
- Log levels are environment-driven via `LOG_LEVEL` (default `INFO`) and `AUDIT_LOG_LEVEL` (default `INFO`) with overrides for development; console output in dev must be human-readable but still structured.
- Retention target: keep roughly 30 days of audit history and two weeks of application logs by rotating 10×5 MB audit files and 5×10 MB app files. This stays within the host-mounted `./data` volume (currently 83 GiB free) while keeping forensic detail.
- Privacy boundaries: never log prompt or note bodies, imported CSV/Markdown text, or file contents; only log metadata (IDs, titles, counts) and validation errors.
- Audit coverage: create/update/delete prompts, version reverts, import/export operations, backup lifecycle actions, and cleanup/compression tasks must produce audit entries that include actor identity (`getpass.getuser()` until auth ships).
- Operational hooks: provide sample `jq` queries and guidance for tailing logs both locally and inside Docker (`./data:/app/data` already mounts logs for the container, so no extra volume is required).
- ValidationMonitor health should be surfaced through structured logs instead of silent failures so on-call staff can detect metric persistence issues.

### Infrastructure Constraints Snapshot

- `data/logs/` already exists and contains `promptvault.log` plus `validation_metrics.json`; current usage is 4 KB (`du -sh data/logs`) on a volume with 83 GiB free (`df -h data/logs`).
- Docker and dev workflows mount `./data` into containers (`docker-compose.yml`), so logs persist on the host by default, but they are not included in prompt data backups—operators must snapshot `data/logs/` separately if compliance requires it.
- `BackupService` only touches `data/backups`, so audit/app logs must avoid being copied into `.json` backups to keep archives lightweight.
- CI/DEV rely on `python run_web.py` (never invoke uvicorn manually); logging bootstrap must therefore live in reusable shared modules, not inside ASGI server CLI entry points.
- Validation metrics currently live alongside logs; the new logging layer must coexist with existing JSON artifacts without race conditions or path conflicts.

### Success Metrics (Also synced to ROADMAP.md)

- `rg "print(" src run_web.py` should return zero matches (tests excluded) after the migration—enforced via CI.
- 100 % of FastAPI routes emit a structured request log containing request ID, method, path, status, latency, and authenticated user (or system user fallback).
- 100 % of critical actions (prompt CRUD, version revert, import/export, backup create/restore/cleanup/compress/delete) emit at least one audit log entry with actor, action, resource, and outcome metadata.
- All exceptions raised inside services descend from `PromptVaultException` (or subclasses) and reach centralized handlers that both log and surface a sanitized JSON error containing the correlation ID.
- ValidationMonitor and frontend telemetry deliver heartbeat logs at least every 15 minutes so operators can confirm instrumentation is alive.

### Phase 2 Implementation Refinements

- Replace every enumerated `print()` call with logging helper invocations—roughly 38 call sites across three services plus the FastAPI layer—so the logging service must expose concise helper APIs for errors, warnings, info, and audit events.
- Because services are instantiated before FastAPI routes load, the logging factory has to be import-safe and lazily configure handlers when `run_web.py` spins up the app (or when CLI scripts call into services).
- Introduce a lightweight context manager (built on `contextvars`) to pass request IDs and actor names down to services invoked outside HTTP contexts (CLI maintenance tasks) so audit logging stays consistent.
- Provide file-permission guards when creating `data/logs/*.log` to avoid Docker-on-mac permission mismatches discovered during Phase 1 (host bind mount owns the directory).
- Build pytest fixtures that can assert log outputs without touching the real `data/logs` directory—Phase 1’s inventory shows side-effect-heavy code paths, so isolation is mandatory for reliable tests.

## Phase 2 – Logging Infrastructure & Configuration
- [x] Select Python logging stack (standard library + `logging.config.dictConfig`) with JSON formatter, rotating file handlers, and optionally console pretty-print for dev; document rationale.
- [x] Create a dedicated `src/services/logging_service.py` encapsulating logger creation, structured context helpers (request_id, actor, action, prompt_id, duration) and environment-driven log level configuration.
- [x] Wire up fast request ID generation (`uuid4().hex`) and propagation via FastAPI middleware storing IDs in `contextvars` for downstream services.
- [x] Configure log destinations: `data/logs/app.log` for application logs, `data/logs/audit.log` for high-value events, ensure Docker/production paths mount volumes and backups exclude sensitive files.
- [x] Replace top-level `print()` usage in bootstrapping scripts (`run_web.py`, CLI helpers) with logger calls, ensuring early initialization uses fallback logger if config fails. *(No bootstrapping prints existed; FastAPI routes now log auto-backup events via the audit logger, satisfying the intent of keeping entrypoints print-free.)*
- [x] Add smoke tests (pytest) verifying logger configuration loads, emits JSON payload, rotates when exceeding threshold (mock `RotatingFileHandler` not required yet—tests assert JSON output and audit/file separation).
- [x] Implementation plan refinement for Phase 3 capturing friction points (e.g., context propagation gaps, handler performance) so the exception strategy fits real logging behavior.

### Phase 2 Outcomes

- **Logging Stack**: Added `src/services/logging_service.py` with `JsonLogFormatter`, rotating file handlers for `app.log` (5×10 MB) and `audit.log` (10×5 MB), and developer-friendly console formatting. `LOG_LEVEL`, `AUDIT_LOG_LEVEL`, and `ENVIRONMENT` env vars control verbosity.
- **Context Propagation**: Introduced `ContextVar`-powered request context plus a FastAPI middleware assigning `X-Request-ID` headers and logging every request with duration, HTTP metadata, and optional actor hints pulled from headers.
- **Audit Hooks**: Automatic backups triggered before delete/import now emit audit entries instead of `print()`, and `ValidationMonitor` failures route through structured logs.
- **Tests**: `tests/test_logging_service.py` confirms JSON output contains request/actor metadata and that audit logs write to their own file, using forced reconfiguration to keep fixtures isolated.

### Phase 3 Implementation Refinements

- Define clear mapping between service exceptions and audit fields so structured error logs can include `prompt_id`, `backup_id`, or `import_job_id` consistently—Phase 2 revealed many service methods mutate state without IDs handy.
- Ensure background/CLI jobs bind an explicit actor (currently defaults to `"anonymous"`); when CLIs run outside FastAPI, they should wrap work in `logging_service.request_context(actor=getpass.getuser())` to keep audit trails meaningful.
- Extend tests to assert log rotation or retention once exception handlers start emitting stack traces—current smoke tests only validate JSON structure.

## Phase 3 – Exception Hierarchy & Centralized Error Handling
- [ ] Define `PromptVaultException` base class plus specialized subclasses (`DataPersistenceError`, `ValidationError`, `AuthenticationError`, `BackupError`, etc.) with standard metadata (http_status, user_message, log_severity).
- [ ] Update services to raise the new exceptions instead of generic `Exception`, ensuring they enrich errors with structured context (prompt_id, backup_id, file_path).
- [ ] Build FastAPI exception handlers that translate each exception class into uniform JSON responses, include correlation/request ID, and emit structured error logs.
- [ ] Add middleware catching unexpected exceptions to ensure they’re logged with stack traces while returning sanitized client responses.
- [ ] Expand unit/integration tests to assert that API routes return consistent payloads and that logger mocks receive expected structured entries when errors occur.
- [ ] Implementation plan refinement for Phase 4 focusing on which operations/events require audit logging versus regular logs, informed by observed exception hotspots.

## Phase 4 – Audit Logging & Observability Enhancements
- [ ] Enumerate critical operations (create/update/delete prompts, version reverts, exports/imports, backups/restores, cleanup/compression) and design audit schemas (timestamp, actor, action, resource_id, diff summary).
- [ ] Instrument the relevant services (PromptDataService, PromptVersioningService, BackupService, PromptImportExportService) to emit audit entries through the logging service, ensuring deduplication and consistent fields.
- [ ] Implement FastAPI middleware capturing request/response metadata (status, latency, payload sizes) and tie into performance metrics for baseline monitoring.
- [ ] Create scripts or docs for log analysis (e.g., sample jq queries, pointers to ELK/Grafana setups) and ensure backups/export flows consider audit logs.
- [ ] Write integration tests verifying audit entries exist for each critical workflow (using tmp log file fixtures) and that sensitive data is excluded/redacted.
- [ ] Implementation plan refinement for Phase 5 summarizing audit rollout feedback and any tooling gaps (log rotation, alerting) to inform frontend telemetry + documentation work.

## Phase 5 – Frontend Error Reporting & Documentation
- [ ] Add TypeScript-ready (or plain JS wrapper for now) error-reporting utility in `src/web/static/js` that funnels `console.error` equivalent data to the backend logging endpoint (include component/action metadata and current locale).
- [ ] Expose a lightweight `/api/logs/frontend` endpoint to accept client error reports, validate payloads, and route them through the logging service with proper rate limiting.
- [ ] Update README.md, AGENTS.md, and docs/ to describe the new logging architecture, configuration knobs (ENV vars), and operational playbooks (rotating logs, investigating incidents).
- [ ] Ensure CHANGELOG.md highlights the new observability capabilities and any operator-impacting changes (new directories, env vars).
- [ ] Implementation plan refinement for post-Phase-5 work, consolidating lessons learned (tooling needs, automation opportunities) for subsequent observability/security initiatives.
