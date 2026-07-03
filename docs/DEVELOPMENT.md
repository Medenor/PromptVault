# Developer Workflow Guide

This page documents the `Makefile` at the repository root, which provides a
unified command surface for common development tasks.

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| **GNU/BSD Make** | 3.81+ | `make --version` |
| **Python** | 3.14+ | `python3 --version` |
| **Node.js** | 20+ | `node --version` |
| **npm** | 10+ | `npm --version` |
| **Docker Compose** | v2 plugin (optional, for `build-image`) | `docker compose version` |

Native Windows is **not supported** directly. Use WSL or Git Bash.

---

## Quick Reference

```sh
make              # show all targets (same as `make help`)
make install      # install all dependencies (backend + frontend)
make dev          # start backend + frontend dev servers
make test         # run full test suite with coverage gates
make lint         # check formatting, lint, and types across both stacks
make lint-fix     # auto-fix formatting and lint issues
make build        # produce production artifacts (frontend + Docker image)
```

---

## All Targets

### Discovery & Guards

| Target | Description |
|--------|-------------|
| `help` | List all targets with descriptions (default action). |
| `check-runtime` | Verify `python3` (>= 3.14) and `node` are available. |
| `check-deps` | Verify `.venv/` and `node_modules/` exist. |

### Installation (US1)

| Target | Description |
|--------|-------------|
| `install` | Install all dependencies (backend first, then frontend). |
| `install-backend` | Create `.venv/` (Python 3.14+) if needed, install project deps + Black. |
| `install-frontend` | Run `npm ci` for reproducible frontend deps. |

### Development Server (US1)

| Target | Description |
|--------|-------------|
| `dev` | Start backend (port 8003) + Vite frontend (port 5173) concurrently. Ctrl-C stops both cleanly. |

Override ports: `PORT=9000 make dev` or `FRONTEND_PORT=3000 make dev`.

**Access the app at `http://localhost:8003/`** — the Vite server at port 5173 is an asset dev server only (hot-reload for static files), not the application itself.

### Testing (US2)

| Target | Description |
|--------|-------------|
| `test` | Run backend + frontend test suites. Fails if either fails. |
| `test-backend` | Run `python3 -m pytest` (coverage gate: 85% via `pytest.ini`). |
| `test-frontend` | Run `npm run test:unit:coverage` (thresholds via `vitest.config.ts`). |

### Linting & Formatting (US3)

| Target | Description |
|--------|-------------|
| `lint` | Check backend (Black + import sanity) and frontend (ESLint + tsc + Prettier). Read-only. |
| `lint-backend` | `black --check src tests` + `pytest --collect-only -q`. |
| `lint-frontend` | `npm run lint` + `npm run typecheck` + `npm run format:check`. |
| `lint-fix` | Auto-fix: `black src tests` + `npm run lint:fix` + `npm run format`. |

### Production Build (US4)

| Target | Description |
|--------|-------------|
| `build` | Build frontend assets + Docker production image. |
| `build-frontend` | `npm run build` (compiled assets in `dist/static/`). |
| `build-image` | `docker compose build web` (production container image). |

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | `8003` | Backend dev server port. |
| `FRONTEND_PORT` | `5173` | Vite dev server port. |

---

## Common Failure Modes

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `ERROR: python3 is not installed` | Missing Python | Install Python 3.14+ |
| `ERROR: Python >= 3.14 is required` | Wrong Python version | Upgrade Python |
| `ERROR: node is not installed` | Missing Node.js | Install Node.js 20+ |
| `ERROR: Virtual environment not found` | Dependencies not installed | Run `make install` |
| `ERROR: node_modules/ not found` | Dependencies not installed | Run `make install` |
| `WARNING: Port 8003 is already in use` | Port conflict | Stop other process or `PORT=<port> make dev` |
| `WARNING: Port 5173 is already in use` | Port conflict | Stop other process or `FRONTEND_PORT=<port> make dev` |

---

## Design Notes

- **Additive only**: the `Makefile` wraps existing canonical commands without
  modifying any source file, script, or deployment definition.
- **POSIX-portable recipes**: no GNU-only constructs where avoidable.
- **Coverage gates** are delegated to each tool's own config (`pytest.ini`,
  `vitest.config.ts`) — the Makefile does not override them.
