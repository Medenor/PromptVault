<h1 align="center">
  <a href="https://codeberg.org/medenor/promptvault">
    <img src="docs/images/promptvault_logo.svg" alt="Logo" width="250" height="250">
  </a>
</h1>

<div align="center">
  PromptVault
  <br />
  <a href="#about"><strong>Explore the screenshots »</strong></a>
  <br />
  <br />
  <a href="https://codeberg.org/medenor/promptvault/issues/new?assignees=&labels=bug&template=01_BUG_REPORT.md&title=bug%3A+">Report a Bug</a>
  ·
  <a href="https://codeberg.org/medenor/promptvault/issues/new?assignees=&labels=enhancement&template=02_FEATURE_REQUEST.md&title=feat%3A+">Request a Feature</a>
  ·
  <a href="https://codeberg.org/medenor/promptvault/issues/new?assignees=&labels=question&template=04_SUPPORT_QUESTION.md&title=support%3A+">Ask a Question</a>
</div>

<div align="center">
<br />

<a href="https://www.gnu.org/licenses/agpl-3.0">
  <img src="https://img.shields.io/badge/License-AGPL%20v3-blue?style=for-the-badge&logo=gnu&logoColor=white" alt="AGPL v3 License">
</a>
<a href="https://www.python.org/">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+">
</a>
<a href="https://fastapi.tiangolo.com/">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
</a>
<a href="https://www.docker.com/">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
</a>
<a href="https://docs.pytest.org/">
  <img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest">
</a>
<a href="https://github.com/psf/black">
  <img src="https://img.shields.io/badge/Code%20Style-Black-000000?style=for-the-badge&logo=python&logoColor=white" alt="Code style: Black">
</a>
<a href="https://codeberg.org/medenor/promptvault/issues">
  <img src="https://img.shields.io/badge/PRs-Welcome-brightgreen?style=for-the-badge&logo=git&logoColor=white" alt="Pull Requests Welcome">
</a>
<a href="https://codeberg.org/medenor/promptvault/">
  <img src="https://img.shields.io/badge/Hosted%20on-Codeberg-2185D0?style=for-the-badge&logo=codeberg&logoColor=white" alt="Hosted on Codeberg">
</a>
<a href="https://codeberg.org/medenor">
  <img src="https://img.shields.io/badge/%3C%2F%3E%20with%20%E2%99%A5%20by-Medenor-ff1414?style=for-the-badge" alt="Created with love by Medenor">
</a>
</div>

<details open="open">
<summary>Table of Contents</summary>

- [About](#about)
  - [Built With](#built-with)
  - [Version Control](#version-control)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Roadmap](#roadmap)
- [Support](#support)
- [Project assistance](#project-assistance)
- [Contributing](#contributing)
- [Authors & contributors](#authors--contributors)
- [Security](#security)
- [License](#license)
- [Acknowledgements](#acknowledgements)

</details>

---

## About

PromptVault is a modern web-based prompt management application designed to help users easily organize, store, and retrieve their prompts for various AI applications, software development, content marketing, and much more. Whether you are a developer, writer, marketer, or simply a user of AI-based tools, PromptVault allows you to centralize your prompts and improve your productivity through a responsive web interface accessible from any browser.

### Built With

- [Python](https://www.python.org/)
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Uvicorn](https://www.uvicorn.org/) - High-performance ASGI server
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine
- [Docker](https://www.docker.com/) - Containerization platform

### Architecture

PromptVault follows a modular architecture with dedicated service classes for different functionalities:

- **PromptDataService**: Handles all data-related operations including loading, saving, and migration of prompt data
- **PromptFilterService**: Manages filtering and searching logic for prompts
- **PromptVersioningService**: Handles version control operations for prompts
- **PromptImportExportService**: Manages import and export operations in various formats (CSV, Markdown)
- **BackupService**: Provides comprehensive data backup and restoration capabilities with automatic pre-operation backups

This modular design improves code maintainability, testability, and extensibility.

### Version Control

PromptVault includes a robust, Git-like version control system for all prompts, ensuring full traceability and a clear history of changes. This feature is **fully implemented and production-ready**. Key features include:

- **Automatic Versioning**: Every update to a prompt automatically creates a new version with complete metadata
- **Unique Version Identifiers**: Each prompt version is assigned a UUID for reliable tracking
- **Detailed Metadata**: Every version tracks essential metadata including timestamp, author, and commit message
- **Version History View**: A dedicated modal dialog allows users to browse a prompt's complete version history with all commits and details
- **Diff Visualization**: Easily compare any two versions to see precise changes in prompt content, title, category, and tags with color-coded highlighting
- **Revert Functionality**: Users can safely revert a prompt to any previous version, which creates a new commit reflecting the reverted state (history is never lost)
- **Keyboard Shortcuts**: Quick access with Cmd+H (Mac) or Ctrl+H (Windows/Linux) to open version history
- **Multi-language Support**: Version control UI available in English, French, Spanish, and German

For detailed usage instructions, see [Version Control Documentation](docs/VERSION_CONTROL.md).

### Data Backup System

PromptVault includes a comprehensive, production-ready backup system to prevent data loss and enable easy recovery:

- **Automatic Backups**: Pre-operation backups are created automatically before risky operations (delete prompts, replace imports)
- **Manual Backups**: Users can create custom-named backups at any time through the web interface
- **Backup Management**: Full-featured backup management page (`/backup-management`) for viewing, restoring, and managing all backups
- **Smart Retention**: Configurable cleanup policies to remove old backups and save disk space
- **Compression**: Automatic gzip compression of older backups to optimize storage usage
- **Safety Features**: Pre-restore backups ensure no data loss during restoration operations
- **Complete Metadata**: Every backup includes comprehensive metadata (timestamp, size, prompt count, author)
- **Maintenance Tools**: Built-in cleanup and compression utilities with progress indicators
- **Statistics Dashboard**: Real-time backup statistics and storage information

<details>
<summary>Screenshots</summary>
<br>

<div align="center">

### Main Interface

<img src="docs/images/promptvault_main_interface.jpg" alt="PromptVault Main Interface" width="80%">

### Import/Export Management

<img src="docs/images/promptvault_import_export.jpg" alt="Import/Export Management Interface" width="80%">

### Prompt Editor

<img src="docs/images/promptvault_prompt_editor.jpg" alt="Prompt Editor Interface" width="80%">

</div>
</details>

## Getting Started

### Prerequisites

- Python 3.8+
- Docker (recommended for production deployment)

### Quick Start with Docker

The fastest way to get started is using Docker:

```bash
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault
docker-compose up --build
```

Then open your browser to `http://localhost:8001`

### Manual Installation

1. **Clone the repository**:

    ```bash
    git clone https://codeberg.org/medenor/promptvault.git
    cd PromptVault
    ```

2. **Create a virtual environment** (recommended):

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3. **Install PromptVault and its dependencies**:

    ```bash
    pip install .
    ```

    For development work you can install in editable mode:

    ```bash
    pip install -e .
    ```

## Usage

### Web Application (Recommended)

PromptVault is primarily a web-based application that runs in your browser and can be deployed as a Docker container.

#### Running with Docker (Production)

```bash
docker-compose up --build
```

Open your browser and go to `http://localhost:8001`

#### Running Locally (Development)

1. Install dependencies:

```bash
pip install -e .
```

2. Run the web application:

```bash
python3 run_web.py
```

By default, the application will run on port 8000. To use a different port, set the `PORT` environment variable:

```bash
PORT=8001 python3 run_web.py
```

3. Open your browser and go to `http://localhost:8000` (or the port you specified)

4. To stop the web application, press `Ctrl+C` in the terminal where the server is running

**Note:** PromptVault is now a web-only application. The legacy desktop version has been deprecated and its startup scripts removed.

### Features

- **Prompt Management**: Create, edit, delete, and organize prompts through an intuitive web interface
- **Version Control**: Git-like versioning system with full history tracking, diff visualization, and safe revert functionality
- **Categories & Tags**: Organize prompts with categories and tags for easy discovery
- **Search & Filter**: Find prompts quickly with advanced filtering and search capabilities
- **Import/Export**: Support for CSV, Markdown, and JSON formats with preview functionality
- **Data Backup System**: Comprehensive backup and restoration with automatic pre-operation backups, manual backups, cleanup, and compression
- **Responsive Design**: Modern, mobile-friendly interface that works on all devices
- **Multi-language Support**: Internationalization with English, French, Spanish, and German

### Internationalization

PromptVault supports multiple languages (English, French, Spanish, German). The application will automatically detect your system language, but you can also change languages from the language selector in the header.

**Translation Files:**

- Web interface uses JSON translation files in `src/web/static/locales/`
- Translations are loaded dynamically using i18next

### Project Structure

The project follows a clean, modular web-first architecture:

- `src/`: Main source code directory
  - `src/web/`: Web application layer
    - `src/web/app.py`: FastAPI application and REST API routes
    - `src/web/templates/`: Jinja2 HTML templates
      - `src/web/templates/index.html`: Main application page
      - `src/web/templates/import_export.html`: Import/export management interface
      - `src/web/templates/backup_management.html`: Backup management interface
    - `src/web/static/`: Static assets
      - `src/web/static/favicon.png`: Application favicon
      - `src/web/static/css/`: Stylesheets
        - `src/web/static/css/style.css`: Main application styles
      - `src/web/static/js/`: JavaScript files
        - `src/web/static/js/app.js`: Main application logic
        - `src/web/static/js/import_export.js`: Import/export functionality
        - `src/web/static/js/backup_management.js`: Backup management functionality
        - `src/web/static/js/types/`: TypeScript type definitions
      - `src/web/static/locales/`: Internationalization files
  - `src/services/`: Business logic and data services
    - `src/services/backup_service.py`: Data backup and restoration
    - `src/services/prompt_data_service.py`: Core data operations
    - `src/services/prompt_filter_service.py`: Search and filtering
    - `src/services/prompt_import_export_service.py`: Import/export functionality
    - `src/services/prompt_versioning_service.py`: Version control system
    - `src/services/version_compression_service.py`: Version compression utilities
    - `src/services/version_export_service.py`: Version export functionality
    - `src/services/version_tagging_service.py`: Version tagging system
- `data/`: Application data files (JSON storage, mounted as Docker volume)
- `docs/`: Documentation and screenshots
  - `docs/CODE_OF_CONDUCT.md`: Code of conduct
  - `docs/CONTRIBUTING.md`: Contributing guidelines
  - `docs/SECURITY.md`: Security policy
  - `docs/images/`: Screenshots and documentation images
- `tests/`: Test suite
  - `tests/conftest.py`: Shared fixtures, factories, and API client helpers
  - `tests/test_prompt_data_service.py`: Core CRUD, persistence, and migration coverage
  - `tests/test_prompt_filter_service.py`: Category/tag/search/favorites filtering
  - `tests/test_prompt_import_export_service.py`: CSV/Markdown import-export scenarios
  - `tests/test_backup_service_extended.py`: Backup/restore/compression edge cases
  - `tests/test_version_compression_service.py`: Compression thresholds and stats
  - `tests/test_version_tagging_service.py`: Tag creation, management, and analytics
  - `tests/test_version_export_service.py`: History/single/comparison exports
  - `tests/test_prompt_versioning_service.py`: Version metadata helpers
  - `tests/test_api_endpoints.py`: FastAPI integration and error handling
  - `tests/test_malformed_data.py`: Corrupted/invalid JSON safeguards
  - `tests/test_performance.py`: Large dataset and export/backup benchmarks
  - `tests/test_backup_system.py`, `tests/test_version_api.py`, `tests/test_version_integration.py`: Legacy regression suites
- `htmlcov/`: Test coverage reports
- `run_web.py`: Web application startup script
- `Dockerfile`: Docker container configuration
- `docker-compose.yml`: Docker Compose configuration for easy deployment
- `pyproject.toml`: Python project configuration and dependencies
- `CHANGELOG.md`: Project changelog
- `LICENSE`: Project license
- `README.md`: This file
- `.gitignore`: Git ignore patterns

## Testing

PromptVault ships with a comprehensive pytest suite that exercises core services, FastAPI endpoints, malformed data handling, and performance characteristics.

### Install test dependencies

```bash
pip install -e .[test]
```

### Run the full suite with coverage

```bash
pytest
```

The default configuration (see `pytest.ini`) enables `--cov=src --cov-report=term-missing --cov-report=html:htmlcov --cov-fail-under=85`, so the run will fail if core coverage drops below 85%. View the detailed HTML report at `htmlcov/index.html`.

### Targeted suites

- Core services only: `pytest tests/test_prompt_data_service.py tests/test_prompt_filter_service.py`
- API endpoints: `pytest tests/test_api_endpoints.py`
- Skip heavy performance tests: `pytest -m "not performance"`
- Performance benchmarks only: `pytest -m performance`

### Performance guardrails

Performance tests in `tests/test_performance.py` enforce the following baselines using synthetic datasets:

- Load/save 1,000 prompts in under 5 seconds
- Load 2,000 version records in under 10 seconds
- Filter/search/sort across 1,000 prompts in under 1 second per operation
- Export 1,000 prompts to CSV/Markdown in under 5 seconds

These targets keep the full suite under ~60 seconds on a modern laptop. Adjust the thresholds by editing the assertions if your deployment environment has different guarantees.

### CI/CD recommendations

1. Pull request gate: `pytest --maxfail=1 --disable-warnings -m "not performance"`
2. Nightly/per-release job: `pytest` (full run, including performance markers)
3. Publish the HTML coverage artifact (`htmlcov/`) to easily inspect regressions.

## Roadmap

For a comprehensive feature improvement roadmap with detailed implementation plans, see [ROADMAP.md](ROADMAP.md).

### Completed Features

- [x] **Version Control System:** Git-like versioning with history tracking, diff visualization, and revert functionality
- [x] **Search & Filtering:** Advanced searching and filtering capabilities across all prompts
- [x] **Data Backup System:** Comprehensive backup and restoration with automatic pre-operation backups, manual backups, cleanup, and compression
- [x] **Unit Tests:** Comprehensive test coverage (85%+) for core functionality with performance benchmarks

### Phase 1: Foundation Strengthening (Priority: High)

- [ ] **Input Validation & Sanitization:** Comprehensive validation framework preventing injection attacks and ensuring data integrity
- [ ] **Error Handling & Logging:** Centralized logging infrastructure with structured logs and audit trails
- [ ] **Performance Monitoring:** Real-time monitoring with APM, error tracking, and analytics dashboards
- [ ] **Accessibility Compliance:** WCAG 2.1 AA compliance with full keyboard navigation and screen reader support

### Phase 2: Security & Architecture (Priority: High)

- [ ] **Authentication & Authorization:** User management with JWT tokens and role-based access control
- [ ] **Database Migration:** Transition from JSON to SQLite/PostgreSQL for improved performance and reliability
- [ ] **TypeScript Migration:** Convert frontend to TypeScript for type safety and better developer experience
- [ ] **API Documentation:** Interactive OpenAPI/Swagger documentation with client SDKs

### Phase 3: User Experience (Priority: Medium)

- [ ] **Pagination & Lazy Loading:** Server-side pagination for handling large datasets efficiently
- [ ] **Advanced Search:** Full-text search, fuzzy matching, saved searches, and advanced filters
- [ ] **Tag & Category Management:** Dedicated interface for managing taxonomy with merge and bulk operations
- [ ] **Mobile UI Enhancements:** Touch-optimized controls, offline support, and mobile-friendly gestures

### Phase 4: Collaboration & Integration (Priority: Medium)

- [ ] **Collaborative Editing:** Real-time updates with WebSockets, presence indicators, and conflict resolution
- [ ] **Enhanced Backup System:** Scheduled backups, cloud storage integration, incremental backups, and encryption
- [ ] **Export & Sharing:** PDF/HTML export, public sharing links, and integrations (Notion, Confluence, Slack)

See [ROADMAP.md](ROADMAP.md) for detailed task breakdowns, implementation estimates, and success metrics.

For proposed features and known issues, visit the [open issues](https://codeberg.org/medenor/promptvault/issues) page.

## Support

Reach out to the maintainer at one of the following places:

- [Codeberg issues](https://codeberg.org/medenor/promptvault/issues)
- Contact options listed on [this Codeberg profile](https://codeberg.org/medenor)

## Project assistance

If you want to say **thank you** or/and support active development of PromptVault:

- Add a [Star](https://codeberg.org/medenor/promptvault) to the project.
- Write interesting articles about the project on [Dev.to](https://dev.to/), [Medium](https://medium.com/) or your personal blog.

Together, we can make PromptVault **better**!

## Contributing

First off, thanks for taking the time to contribute! Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make will benefit everybody else and are **greatly appreciated**.

Please read our contribution guidelines, and thank you for being involved!

## Authors & contributors

The original setup of this repository is by [Medenor](https://codeberg.org/medenor).

For a full list of all authors and contributors, see [the contributors page](https://codeberg.org/medenor/promptvault/graphs/contributors).

## Security

PromptVault follows good practices of security, but 100% security cannot be assured.
PromptVault is provided **"as is"** without any **warranty**. Use at your own risk.

## License

This project is licensed under the **GNU AGPLv3 license**.

See [LICENSE](LICENSE) for more information.

## Acknowledgements

- Repository files templates provided by [dec0dOS/amazing-github-template](https://github.com/dec0dOS/amazing-github-template)
