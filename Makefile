# ==============================================================================
# PromptVault — Developer Workflow Makefile
# ==============================================================================
#
# Single entry point for common development tasks.
# Additive only: wraps existing canonical commands without modifying any
# source file, script, or deployment definition.
#
# Usage:
#   make              # show this help (default)
#   make <target>     # run a specific target
#   make help         # list all targets
#
# See docs/DEVELOPMENT.md for prerequisites, environments, and failure modes.
# ==============================================================================

# ------------------------------------------------------------------------------
# Recipe-time variables
# ------------------------------------------------------------------------------
PYTHON           := .venv/bin/python
PIP              := .venv/bin/pip
VENV_DIR         := .venv
BACKEND_PORT     ?= 8003
FRONTEND_PORT    ?= 5173
PYTEST           := $(PYTHON) -m pytest
BACKEND_TEST_CMD  = $(PYTEST)
FRONTEND_TEST_CMD = npm run test:unit:coverage
COMPOSE          := docker compose

# ------------------------------------------------------------------------------
# Phony declarations (all targets — no file artifacts)
# ------------------------------------------------------------------------------
.PHONY: help \
        check-runtime check-deps \
        install install-backend install-frontend \
        dev \
        test test-backend test-frontend \
        lint lint-backend lint-frontend lint-fix \
        build build-frontend build-image

.DEFAULT_GOAL := help

# ==============================================================================
# Self-documentation
# ==============================================================================

help: ## Show this help message (default target)
	@echo "PromptVault — Developer Workflow"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /|/' | awk -F'|' '{printf "  %-22s %s\n", $$1, $$2}'

# ==============================================================================
# Safety guards
# ==============================================================================

check-runtime: ## Verify required runtimes are available (python3 >= 3.14, node)
	@command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is not installed or not in PATH."; echo "       Install Python 3.14+ and retry."; exit 1; }
	@python3 -c "import sys; v=sys.version_info[:2]; exit(0 if v >= (3,14) else 1)" 2>/dev/null || { echo "ERROR: Python >= 3.14 is required (found $$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo 'unknown'))."; echo "       Upgrade Python and retry."; exit 1; }
	@command -v node >/dev/null 2>&1 || { echo "ERROR: node is not installed or not in PATH."; echo "       Install Node.js 20+ and retry."; exit 1; }

check-deps: ## Verify dependencies are installed (.venv and node_modules exist)
	@if [ ! -d "$(VENV_DIR)" ]; then echo "ERROR: Virtual environment not found ($(VENV_DIR)/)."; echo "       Run 'make install' first."; exit 1; fi
	@if [ ! -d "node_modules" ]; then echo "ERROR: node_modules/ not found."; echo "       Run 'make install' first."; exit 1; fi

# ==============================================================================
# US1 — Fast Onboarding (install + dev)
# ==============================================================================

install-backend: ## Install backend dependencies (create .venv if needed)
	@_recreate=0; \
	if [ ! -d "$(VENV_DIR)" ]; then \
		_recreate=1; \
	elif ! $(PYTHON) -c "import sys; exit(0 if sys.version_info[:2] >= (3,14) else 1)" 2>/dev/null; then \
		echo "Existing $(VENV_DIR)/ has Python < 3.14 — recreating..."; \
		rm -rf $(VENV_DIR); \
		_recreate=1; \
	fi; \
	if [ "$$_recreate" -eq 1 ]; then \
		echo "Creating virtual environment in $(VENV_DIR)/ ..."; \
		python3 -m venv $(VENV_DIR); \
	fi
	$(PIP) install -e ".[test]"
	$(PIP) install black

install-frontend: ## Install frontend dependencies (npm ci)
	npm ci

install: install-backend install-frontend ## Install all dependencies (backend then frontend)

dev: ## Start backend + frontend dev servers concurrently (Ctrl-C to stop)
	@$(MAKE) --no-print-directory check-deps
	@echo "Starting development servers..."
	@_backend_ok=1; _frontend_ok=1; \
	if command -v lsof >/dev/null 2>&1; then \
		if lsof -i :$(BACKEND_PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
			echo "WARNING: Port $(BACKEND_PORT) is already in use."; \
			echo "         Stop the other process or set PORT=<port> and retry."; \
			_backend_ok=0; \
		fi; \
		if lsof -i :$(FRONTEND_PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
			echo "WARNING: Port $(FRONTEND_PORT) is already in use."; \
			echo "         Stop the other process or set FRONTEND_PORT=<port> and retry."; \
			_frontend_ok=0; \
		fi; \
	elif command -v nc >/dev/null 2>&1; then \
		if nc -z localhost $(BACKEND_PORT) 2>/dev/null; then \
			echo "WARNING: Port $(BACKEND_PORT) is already in use."; \
			echo "         Stop the other process or set PORT=<port> and retry."; \
			_backend_ok=0; \
		fi; \
		if nc -z localhost $(FRONTEND_PORT) 2>/dev/null; then \
			echo "WARNING: Port $(FRONTEND_PORT) is already in use."; \
			echo "         Stop the other process or set FRONTEND_PORT=<port> and retry."; \
			_frontend_ok=0; \
		fi; \
	fi; \
	if [ "$$_backend_ok" -eq 0 ] || [ "$$_frontend_ok" -eq 0 ]; then \
		echo ""; \
	fi
	@_pids=""; \
	cleanup() { \
		echo ""; \
		echo "Shutting down dev servers..."; \
		if [ -n "$$_pids" ]; then \
			kill $$_pids 2>/dev/null; \
			wait $$_pids 2>/dev/null; \
		fi; \
		echo "Done."; \
	}; \
	trap cleanup INT TERM EXIT; \
	echo "  Backend:  http://localhost:$(BACKEND_PORT)"; \
	echo "  Frontend: http://localhost:$(FRONTEND_PORT) (asset server only)"; \
	echo "  App:      http://localhost:$(BACKEND_PORT)/"; \
	echo ""; \
	$(PYTHON) run_web.py & \
	_pids="$$!"; \
	npm run dev & \
	_pids="$$_pids $$!"; \
	echo "Press Ctrl-C to stop both servers."; \
	wait

# ==============================================================================
# US2 — Run the Full Test Suite
# ==============================================================================

test-backend: ## Run backend test suite with coverage (python3 -m pytest)
	$(BACKEND_TEST_CMD)

test-frontend: ## Run frontend test suite with coverage (vitest)
	$(FRONTEND_TEST_CMD)

test: ## Run all test suites (backend + frontend) with coverage gates
	@echo "=== Running full test suite ==="
	@_fail=0; \
	echo ""; \
	echo "--- Backend tests ---"; \
	$(BACKEND_TEST_CMD) || _fail=1; \
	echo ""; \
	echo "--- Frontend tests ---"; \
	$(FRONTEND_TEST_CMD) || _fail=1; \
	echo ""; \
	if [ "$$_fail" -ne 0 ]; then \
		echo "=== RESULT: FAIL (one or more suites failed) ==="; \
		exit 1; \
	else \
		echo "=== RESULT: PASS (all suites passed) ==="; \
	fi

# ==============================================================================
# US3 — Lint and Format
# ==============================================================================

lint-backend: ## Check backend formatting (black --check) + import sanity
	$(PYTHON) -m black --check src tests
	$(PYTEST) --collect-only -q

lint-frontend: ## Check frontend lint + typecheck + formatting
	npm run lint
	npm run typecheck
	npm run format:check

lint: lint-backend lint-frontend ## Run all lint/format checks across both stacks (read-only)

lint-fix: ## Auto-fix formatting and lint issues in place
	$(PYTHON) -m black src tests
	npm run lint:fix
	npm run format

# ==============================================================================
# US4 — Production Build
# ==============================================================================

build-frontend: ## Build frontend assets (TypeScript + Vite → dist/static/)
	npm run build

build-image: ## Build production Docker image via Compose
	$(COMPOSE) build web

build: build-frontend build-image ## Build all production artifacts (frontend + Docker image)
