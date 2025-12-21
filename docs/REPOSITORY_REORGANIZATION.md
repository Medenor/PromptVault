# PromptVault Repository Restructuring - Detailed Migration Strategy

## Executive Summary

This document provides a comprehensive, granular migration strategy for restructuring the PromptVault repository from the current `src/` organization to a modern `app/` architecture. The migration will improve code organization, maintainability, and align with industry best practices for Python web applications.

## Migration Overview

**Current Structure:** `src/` based organization
**Target Structure:** `app/` based organization  
**Migration Type:** In-place restructuring with backward compatibility
**Estimated Duration:** 3-4 hours for complete migration and validation
**Risk Level:** Low (with proper rollback procedures)

---

## Phase 1: Foundation Setup and Analysis

### 1.1 Pre-Migration Analysis and Backup

#### 1.1.1 Repository State Validation

- [ ] **Verify Git Status**

  ```bash
  git status
  git diff --stat
  git log --oneline -10
  ```

- [ ] **Create Backup Branch**

  ```bash
  git checkout -b backup-pre-migration
  git push origin backup-pre-migration
  git checkout main
  ```

- [ ] **Document Current Package Dependencies**

  ```bash
  find src/ -name "*.py" -exec grep -l "^from\|^import" {} \; > current_imports.txt
  grep -r "from src\|import src" . --include="*.py" --include="*.toml" --include="*.ini" > src_references.txt
  ```

#### 1.1.2 Build System Analysis

- [ ] **Analyze Current Build Configuration**
  - Review `pyproject.toml` package discovery
  - Check `pytest.ini` coverage settings
  - Validate `alembic.ini` configuration
  - Examine `Dockerfile` and `docker-compose.yml` for package references

#### 1.1.3 Import Mapping Creation

- [ ] **Generate Complete Import Map**

  ```bash
  # Create comprehensive mapping of all imports
  python3 -c "
  import ast
  import os
  from pathlib import Path

  src_files = list(Path('src').rglob('*.py'))
  import_map = {}

  for file in src_files:
      with open(file) as f:
          try:
              tree = ast.parse(f.read())
              for node in ast.walk(tree):
                  if isinstance(node, (ast.ImportFrom, ast.Import)):
                      # Process imports
          except:
              pass
  "
  ```

### 1.2 Directory Structure Creation

#### 1.2.1 New Directory Structure Setup

- [ ] **Create Target Directory Structure**

  ```bash
  mkdir -p app/{config,db/{models,repositories},services/{auth},web/{dependencies,middleware,models,monitoring,routers,static/{css,js,locales},templates/{admin,auth},validators}}
  ```

- [ ] **Verify Directory Structure**

  ```bash
  tree app/ -d
  ```

#### 1.2.2 Preserve Special Directories

- [ ] **Identify and Preserve Non-Python Directories**
  - `app/web/static/` (CSS, JS, images, locales)
  - `app/web/templates/` (HTML templates)
  - `app/config/` (Configuration files)

### 1.3 Package Content Migration

#### 1.3.1 Core Package Migration

- [ ] **Migrate Configuration Layer**

  ```bash
  cp -r src/config/* app/config/
  ```

- [ ] **Migrate Database Layer**

  ```bash
  cp -r src/db/* app/db/
  # Preserve __init__.py files
  find app/db -name "*.py" -exec chmod 644 {} \;
  ```

- [ ] **Migrate Services Layer**

  ```bash
  cp -r src/services/* app/services/
  # Handle auth subdirectory specifically
  cp -r src/services/auth/* app/services/auth/ 2>/dev/null || true
  ```

- [ ] **Migrate Web Layer**

  ```bash
  cp -r src/web/* app/web/
  # Preserve static files and templates
  ```

#### 1.3.2 File Integrity Verification

- [ ] **Verify File Count Match**

  ```bash
  find src -name "*.py" | wc -l > src_count.txt
  find app -name "*.py" | wc -l > app_count.txt
  diff src_count.txt app_count.txt
  ```

- [ ] **Binary File Preservation**

  ```bash
  find src/web/static -type f ! -name "*.py" > src_static_files.txt
  find app/web/static -type f ! -name "*.py" > app_static_files.txt
  diff src_static_files.txt app_static_files.txt
  ```

---

## Phase 2: Import Statement Updates

### 2.1 Automated Import Migration

#### 2.1.1 Python Import Path Updates

- [ ] **Update Absolute Imports**

  ```bash
  # Search and replace pattern: from src.config -> from app.config
  find app -name "*.py" -type f -exec sed -i '' 's/from src\./from app\./g' {} \;
  find app -name "*.py" -type f -exec sed -i '' 's/import src\./import app\./g' {} \;
  ```

#### 2.1.2 Configuration File Updates

- [ ] **Update pyproject.toml**

  ```toml
  # Original: [tool.setuptools.packages.find]
  # where = ["."]
  # include = ["src*"]

  # Updated:
  [tool.setuptools.packages.find]
  where = ["."]
  include = ["app*"]
  ```

- [ ] **Update pytest.ini**

  ```ini
  # Original: --cov=src
  # Updated:
  --cov=app
  ```

- [ ] **Update alembic.ini**

  ```ini
  # Check for any src references in script location
  sed -i '' 's/src/app/g' alembic.ini
  ```

#### 2.1.3 Docker Configuration Updates

- [ ] **Update Dockerfile**

  ```dockerfile
  # Check WORKDIR and any src references
  # Update to use app/ instead of src/
  ```

- [ ] **Update docker-compose.yml**

  ```yaml
  # Review volumes and environment for src references
  ```

### 2.2 Manual Import Verification

#### 2.2.1 Complex Import Pattern Handling

- [ ] **Handle Relative Imports**

  ```python
  # Review files with relative imports like:
  # from .config import settings
  # from ..db.models import User
  # Update paths as needed
  ```

- [ ] **Alias and Star Imports**

  ```python
  # Verify star imports still work:
  # from app.db.models import *
  # Ensure __init__.py files are complete
  ```

#### 2.2.2 Circular Import Resolution

- [ ] **Detect Circular Imports**

  ```bash
  python3 -m py_compile app/config/auth_config.py
  python3 -m py_compile app/db/base.py
  # Test compilation of all files
  find app -name "*.py" -exec python3 -m py_compile {} \;
  ```

### 2.3 Import Validation and Testing

#### 2.3.1 Basic Import Testing

- [ ] **Test Core Module Imports**

  ```python
  # Create test_imports.py
  try:
      from app.config.auth_config import *
      from app.db.base import *
      from app.services.auth import *
      from app.web.app import *
      print("All imports successful")
  except ImportError as e:
      print(f"Import error: {e}")
  ```

#### 2.3.2 Package Structure Validation

- [ ] **Verify Package Discovery**

  ```bash
  python3 -c "import app; print(app.__path__)"
  python3 -c "import app.config; print(app.config.__path__)"
  ```

---

## Phase 3: Configuration and Build System Updates

### 3.1 Build System Migration

#### 3.1.1 Setuptools Configuration

- [ ] **Update pyproject.toml Package Discovery**

  ```toml
  [tool.setuptools.packages.find]
  where = ["."]
  include = ["app*"]
  exclude = ["app.*.tests*", "app.tests*"]
  ```

#### 3.1.2 Coverage Configuration Update

- [ ] **Update Coverage Settings**

  ```ini
  [coverage:run]
  source = ["app"]
  omit = [
      "*/tests/*",
      "*/__pycache__/*",
      "*/venv/*",
      "*/.venv/*",
      "*/alembic/*",
  ]
  ```

#### 3.1.3 Test Configuration Migration

- [ ] **Update pytest.ini Coverage Path**

  ```ini
  [pytest]
  # ...
  addopts =
      --verbose
      --cov=app
      --cov-report=term-missing
      --cov-report=html:htmlcov
      --cov-fail-under=85
      -ra
  ```

### 3.2 Database Configuration Updates

#### 3.2.1 Alembic Configuration Review

- [ ] **Check Alembic Script Location**

  ```ini
  # In alembic.ini
  script_location = alemic
  # Should remain unchanged
  ```

- [ ] **Verify Database Model Imports**

  ```python
  # In alembic/env.py
  # Check import paths for database models
  from app.db.base import Base
  # instead of: from src.db.base import Base
  ```

### 3.3 Web Application Configuration

#### 3.3.1 FastAPI Application Updates

- [ ] **Update Application Entry Point**

  ```python
  # In app/web/app.py
  # Verify all imports use app. prefix
  from app.config.auth_config import settings
  from app.db.session import SessionLocal
  ```

#### 3.3.2 Static Files Path Updates

- [ ] **Check Static Files Configuration**

  ```python
  # Verify static files mount point still works
  app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
  ```

---

## Phase 4: Application Functionality Testing

### 4.1 Unit Testing Validation

#### 4.1.1 Test Import Updates

- [ ] **Update Test File Imports**

  ```python
  # In all test files, update:
  # from src.config.auth_config import *
  # to:
  from app.config.auth_config import *
  ```

#### 4.1.2 Test Configuration Updates

- [ ] **Update Test Configuration Files**

  ```python
  # In tests/conftest.py
  # Update import paths to use app.
  ```

#### 4.1.3 Run Core Test Suite

- [ ] **Execute Test Suite**

  ```bash
  python3 -m pytest tests/ -v
  python3 -m pytest tests/ --cov=app --cov-report=term
  ```

### 4.2 Integration Testing

#### 4.2.1 Application Startup Testing

- [ ] **Test Web Application Launch**

  ```bash
  python3 run_web.py
  # Verify no import errors during startup
  ```

#### 4.2.2 Database Connection Testing

- [ ] **Test Database Operations**

  ```python
  # Test database initialization
  from app.db.base import Base
  from app.db.session import engine
  Base.metadata.create_all(bind=engine)
  ```

#### 4.2.3 Authentication System Testing

- [ ] **Test Authentication Imports**

  ```python
  from app.services.auth.auth_service import AuthService
  from app.services.auth.jwt_service import JWTService
  ```

### 4.3 End-to-End Testing

#### 4.3.1 API Endpoint Testing

- [ ] **Test Key API Endpoints**

  ```bash
  curl -X GET http://localhost:8003/ -I
  curl -X GET http://localhost:8003/api/prompts -H "Authorization: Bearer <token>"
  ```

#### 4.3.2 Web Interface Testing

- [ ] **Test Web Interface**
  - Access main page
  - Test authentication flows
  - Verify static file loading

---

## Phase 5: Documentation Updates

### 5.1 Code Documentation Updates

#### 5.1.1 Docstring Import References

- [ ] **Update Code Documentation**

  ```python
  # Update docstrings that reference old import paths
  """
  Example:
  from app.config.auth_config import settings  # Updated from src.config
  """
  ```

#### 5.1.2 README and Guide Updates

- [ ] **Update Installation Instructions**

  ```markdown
  # Update pip install instructions if needed

  # Update Docker volume mounts

  # Update development setup instructions
  ```

### 5.2 Configuration Documentation

#### 5.2.1 Development Guide Updates

- [ ] **Update Development Setup Guide**
  - Update file path references
  - Update import statement examples
  - Update testing instructions

#### 5.2.2 API Documentation

- [ ] **Update OpenAPI Documentation**

  ```python
  # Verify API documentation generation still works
  # Check for any hardcoded import references
  ```

### 5.3 Deployment Documentation

#### 5.3.1 Docker Documentation

- [ ] **Update Docker Deployment Guides**
  - Review docker-compose.yml references
  - Update volume mount paths
  - Update environment variable examples

#### 5.3.2 Production Deployment

- [ ] **Update Production Deployment Guides**
  - Review nginx configuration examples
  - Update systemd service files
  - Update CI/CD pipeline configurations

---

## Phase 6: Development Environment Configuration

### 6.1 IDE Configuration Updates

#### 6.1.1 VSCode Settings

- [ ] **Update .vscode/settings.json**

  ```json
  {
    "python.analysis.extraPaths": ["./app"],
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
  }
  ```

#### 6.1.2 Git Configuration

- [ ] **Update .gitignore**

  ```gitignore
  # Ensure __pycache__ and .pyc files are still ignored
  app/**/__pycache__/
  app/**/*.pyc
  ```

### 6.2 Pre-commit Hooks Configuration

#### 6.2.1 Update Pre-commit Configuration

- [ ] **Check and Update pre-commit hooks**

  ```yaml
  # Ensure hooks work with new app structure
  repos:
    - repo: local
      hooks:
        - id: pytest
          name: pytest
          entry: python3 -m pytest
          language: system
          pass_filenames: false
  ```

### 6.3 Development Scripts Updates

#### 6.3.1 Operational Scripts Migration

- [ ] **Update Script Imports**

  ```python
  # In scripts/ directory, update:
  # from src.config import settings
  # to:
  from app.config import settings
  ```

#### 6.3.2 Create Development Helper Scripts

- [ ] **Create Migration Verification Script**

  ```python
  # scripts/verify_migration.py
  # Verify all imports work correctly
  ```

---

## Phase 7: CI/CD Pipeline Updates

### 7.1 GitHub Actions/GitLab CI Updates

#### 7.1.1 Update CI Configuration

- [ ] **Update Workflow Files**

  ```yaml
  # Update paths in CI/CD workflows
  # Update test commands to use app coverage
  # Update docker build contexts
  ```

#### 7.1.2 Update Docker Build Process

- [ ] **Review Docker Build Pipeline**

  ```dockerfile
  # Ensure WORKDIR and COPY commands use app/
  WORKDIR /app
  COPY . .
  ```

### 7.2 Testing Pipeline Updates

#### 7.2.1 Update Test Commands

- [ ] **CI Test Commands Update**

  ```bash
  # Update to use app coverage
  python3 -m pytest --cov=app --cov-report=xml
  ```

#### 7.2.2 Security Scanning Updates

- [ ] **Update Security Scanning**

  ```bash
  # Update bandit, safety, etc. to scan app/ directory
  bandit -r app/
  safety check --path app/
  ```

---

## Phase 8: Final Validation and Cleanup

### 8.1 Complete System Validation

#### 8.1.1 Comprehensive Testing

- [ ] **Run Full Test Suite**

  ```bash
  python3 -m pytest --cov=app --cov-report=html --cov-fail-under=85
  ```

#### 8.1.2 Performance Benchmarking

- [ ] **Compare Pre/Post Migration Performance**

  ```python
  # Measure import times
  import time
  start = time.time()
  from app.web.app import app
  import_time = time.time() - start
  print(f"Import time: {import_time:.3f}s")
  ```

### 8.2 Code Quality Validation

#### 8.2.1 Static Analysis

- [ ] **Run Code Quality Tools**

  ```bash
  flake8 app/
  black --check app/
  mypy
  ```
