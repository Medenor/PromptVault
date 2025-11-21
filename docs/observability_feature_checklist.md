# Observability & Telemetry Feature Checklist

Use this checklist to validate the full centralized logging, auditing, and telemetry stack (Phases 1–5 of Issue #10). Complete all sections before signing off a release.

## Prerequisites

- [ ] Clean virtual environment activated (`python -m venv .venv && source .venv/bin/activate`)
- [ ] Dependencies installed (`pip install -e .[dev]`)
- [ ] Data/logs directory writable (`data/logs/app.log`, `data/logs/audit.log`)
- [ ] Browser available for manual UI checks (Chrome/Firefox latest recommended)

---

## Phase 1 – Baseline Validation

- [ ] Search the codebase for stray `print(` or bare `except:` and confirm none remain in `src/services`, `src/web`, or `run_web.py`.
- [ ] Run `pytest -k "not performance"` and confirm all existing tests pass with coverage ≥85%.
- [ ] Verify `docs/plan_centralized_error_logging.md` reflects the current architecture notes gathered in Phase 1.

---

## Phase 2 – Structured Logging Foundation

- [ ] Start the app (`python run_web.py`), hit `GET /api/prompts`, and confirm `data/logs/app.log` records request logs with `request_id`, `actor`, `event`, and `duration_ms`.
- [ ] Trigger a server-side error (e.g., send malformed payload to `/api/prompts`) and check that the log entry includes stack trace metadata without crashing the server.
- [ ] Verify `request_id` is returned in response headers (`X-Request-ID`) for both success and error cases.

---

## Phase 3 – Exception Framework Integration

- [ ] Directly exercise services via tests: `pytest tests/test_prompt_data_service.py tests/test_backup_service.py tests/test_prompt_import_export_service.py`.
- [ ] Confirm `src/services/exceptions.py` classes surface in logs when forcing errors (e.g., delete data file then call `PromptDataService.load_prompts()`).
- [ ] Verify FastAPI exception handlers return structured JSON errors matching tests in `tests/test_api_endpoints.py`.

---

## Phase 4 – Audit Logging Coverage

- [ ] Use the UI (or API) to create, update, delete, and revert prompts; confirm each action appends an audit entry to `data/logs/audit.log` with correct `action`, `resource_id`, and `actor`.
- [ ] Perform backup operations (create, restore, delete, cleanup, compress) and verify matching audit entries plus success/warning logs.
- [ ] Run `pytest tests/test_audit_logging.py tests/test_backup_service_coverage.py tests/test_backup_service_extended.py` and ensure they pass without regressions.
- [ ] Inspect `docs/plan_centralized_error_logging.md` Phase 4 outcomes and verify they match observed behavior.

---

## Phase 5 – Frontend Telemetry & Documentation

- [ ] Load every template (`/`, `/import-export`, `/backup-management`) and confirm `telemetry.js` is requested before other app scripts.
- [ ] In the browser console, execute `FrontendLogger.isEnabled()` to confirm telemetry is active, then call `FrontendLogger.disable()` and ensure error reports stop (verify via backend logs).
- [ ] Trigger a UI error (e.g., disconnect network and attempt an export). Confirm `window.FrontendLogger` sends a report (`/api/logs/frontend` returns 200) and that a structured log entry appears with `event=frontend.error`.
- [ ] Run `pytest tests/test_api_endpoints.py -k FrontendLogging` to ensure rate limiting and validation rules hold.
- [ ] Review README/AGENTS/plan updates for telemetry guidance and confirm they match the implemented behavior.

---

## Final Regression Sweep

- [ ] Execute the full suite: `pytest` (including performance tests if required by CI policy).
- [ ] Manually sanity-check key UI flows (prompt CRUD, import/export, backups) to ensure telemetry additions did not introduce visual or functional regressions.
- [ ] Archive sample `app.log`/`audit.log` files for release artifacts or attach to the release ticket as evidence.

When all boxes are checked, the centralized logging & telemetry feature is validated end-to-end.
