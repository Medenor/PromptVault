<h1 align="center">
  <a href="https://codeberg.org/medenor/promptvault">
    <img src="docs/images/promptvault_logo.jpg" alt="Logo" width="50%">
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

<a href="https://www.mozilla.org/en-US/MPL/2.0/">
  <img src="https://img.shields.io/badge/MPL--2.0-blue?style=for-the-badge&logo=mozilla&logoColor=white" alt="MPL-2.0 License">
</a>
<a href="https://www.python.org/">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
</a>
<a href="https://www.typescriptlang.org/">
  <img src="https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
</a>
<a href="https://fastapi.tiangolo.com/">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
</a>
<a href="https://vitejs.dev/">
  <img src="https://img.shields.io/badge/Vite-5.x-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite">
</a>
<a href="https://www.docker.com/">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
</a>
<a href="https://docs.pytest.org/">
  <img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest">
</a>
<a href="https://vitest.dev/">
  <img src="https://img.shields.io/badge/Vitest-6E9F18?style=for-the-badge&logo=vitest&logoColor=white" alt="Vitest">
</a>
<a href="https://eslint.org/">
  <img src="https://img.shields.io/badge/ESLint-4B32C3?style=for-the-badge&logo=eslint&logoColor=white" alt="ESLint">
</a>
<a href="https://prettier.io/">
  <img src="https://img.shields.io/badge/Prettier-F7B93E?style=for-the-badge&logo=prettier&logoColor=white" alt="Prettier">
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
  - [Screenshots](#screenshots-and-gallery)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Authentication](#authentication)
  - [User Roles](#user-roles)
  - [Security Features](#security-features)
  - [First-Time Setup](#first-time-setup)
- [Usage](#usage)
- [Roadmap](#roadmap)
- [Support](#support)
- [Project assistance](#project-assistance)
- [Contributing](#contributing)
- [Authors & contributors](#authors--contributors)
- [Security](#security)
- [License](#license)
- [Disclaimer](#disclaimer-vibe-coding-ai-assistance)
- [Acknowledgements](#acknowledgements)

</details>

---

## About

PromptVault is a modern web-based prompt management application designed to help users easily organize, store, and retrieve their prompts for various AI applications, software development, content marketing, and much more. Whether you are a developer, writer, marketer, or simply a user of AI-based tools, PromptVault allows you to centralize your prompts and improve your productivity through a responsive web interface accessible from any browser.

With built-in multi-user authentication and role-based access control, PromptVault is ready for team deployments and production environments. Secure your prompts, manage user permissions, and collaborate with confidence.

#### Current Status & Test Coverage

PromptVault is **fully tested and production-ready**:

- **Backend Testing**: 1,087 Python unit tests passing (83.54% coverage) with full integration tests
- **Frontend Testing**: 49 TypeScript unit tests passing (89.83% coverage) with component and utility tests
- **UI Redesign**: Complete Tailwind CSS v4 migration with responsive design and improved accessibility
- **Security**: Comprehensive security configuration with JWT ES256 authentication, password hashing, rate limiting, and session management
- **Internationalization**: Full i18n support for English, French, Spanish, and German

### Built With

- [Python](https://www.python.org/) 3.11+
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Uvicorn](https://www.uvicorn.org/) - High-performance ASGI server
- [TypeScript](https://www.typescriptlang.org/) - Frontend logic (migration complete)
- [Vite](https://vitejs.dev/) - Frontend build and dev server
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [PostgreSQL](https://www.postgresql.org/) / [SQLite](https://www.sqlite.org/) - Database backends
- [Alembic](https://alembic.sqlalchemy.org/) - Database migrations
- [Docker](https://www.docker.com/) - Containerization platform
- [Argon2](https://github.com/p-h-c/phc-winner-argon2) - Password hashing (OWASP recommended)
- [PyJWT](https://pyjwt.readthedocs.io/) - JWT token authentication with ES256
- [slowapi](https://github.com/laurents/slowapi) - Rate limiting for authentication endpoints
- [Vitest](https://vitest.dev/) - Frontend unit tests and coverage
- [ESLint](https://eslint.org/) / [Prettier](https://prettier.io/) - Frontend linting and formatting

### Architecture

PromptVault follows a clean, layered architecture with clear separation of concerns:

**Service Layer:**

- **PromptDataService**: Handles all data-related operations including loading, saving, and migration of prompt data
- **PromptFilterService**: Manages filtering and searching logic for prompts
- **PromptVersioningService**: Handles version control operations for prompts
- **PromptImportExportService**: Manages import and export operations in various formats (CSV, Markdown)
- **BackupService**: Provides comprehensive data backup and restoration capabilities with automatic pre-operation backups

**Data Layer (Database Backend):**

- **Repository Pattern**: Abstract data access through specialized repositories (PromptRepository, VersionRepository, CategoryRepository, TagRepository)
- **ORM Models**: SQLAlchemy models for type-safe database operations
- **Session Management**: Context managers for transaction safety and automatic rollback
- **Migration Support**: Alembic-based database versioning and schema evolution

**Storage Options:**

- **PostgreSQL**: Production-ready relational database for high-performance, concurrent access (recommended for production)
- **SQLite**: Lightweight embedded database for development and small deployments
- **JSON (Legacy)**: File-based storage for backward compatibility (deprecated)

This modular design improves code maintainability, testability, and extensibility while providing flexibility in deployment options.

For detailed technical specifications and database schema, see [Database Specification](docs/SPECS/SPEC_DATABASE.md). For development guidelines and codebase structure, see [AGENTS.md](docs/AGENTS.md).

### UI Design & Styling

PromptVault's frontend has been modernized with Tailwind CSS v4 for consistent, responsive UI:

- **Tailwind CSS v4**: Utility-first CSS framework with @theme directives for custom design system
- **Responsive Design**: Mobile-first approach with breakpoints for all device sizes
- **Dark Mode Ready**: Tailwind color palette supports light and dark themes
- **Component Library**: Reusable button, card, form, input, and navigation components
- **Accessibility**: Focus states, keyboard navigation, ARIA labels, and semantic HTML
- **Performance**: CSS purging and optimization for minimal bundle size

### TypeScript Migration

PromptVault's frontend has been migrated from legacy JavaScript to TypeScript. All page scripts now live under `src/web/static/ts`, are built via Vite, and type-checked with `tsc`. Legacy JS under `src/web/static/js` remains only for historical reference and should not be edited for new work.

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

## Screenshots and gallery
<details>
<summary>Click to expand</summary>
<br>

<div align="center">

### Key Features Gallery

#### 1. Login Page

<img src="docs/images/gallery/promptvault_loginpage.jpg" alt="PromptVault Login Page" width="90%"><br/>
Tailwind v4 flat-design login screen with JWT authentication and password reset access.

<br><br>

#### 2. Main Interface

<img src="docs/images/gallery/promptvault_main_page.jpg" alt="PromptVault Main Interface" width="90%"><br/>
Modern prompt dashboard with filter sidebar, tag chips, and responsive card grid.

<br><br>

#### 3. Prompt Editor

<img src="docs/images/gallery/promptvault_prompt_editor.jpg" alt="Prompt Editor Interface" width="90%"><br/>
Redesigned prompt editor with structured fields, categories, tags, and commit messaging.

<br><br>

#### 4. Version History & Diff Visualization

<img src="docs/images/gallery/promptvault_version_history.jpg" alt="Version History" width="90%"><br/>
Version history modal with searchable entries, revert actions, and quick selection.

<br><br>

#### 5. Import/Export Management

<img src="docs/images/gallery/promptvault_import_export.jpg" alt="Import/Export Management Interface" width="90%"><br/>
Import/export hub with side-by-side panels, format options, and live statistics.

<br><br>

#### 6. Data Backup System

<img src="docs/images/gallery/promptvault_backup.jpg" alt="Backup Management Interface" width="90%"><br/>
Backup management view with create/restore actions, maintenance tools, and stats.

<br><br>

#### 7. User Profile Management

<img src="docs/images/gallery/promptvault_user_profile.jpg" alt="User Profile Interface" width="90%"><br/>
Profile page with preferences, security controls, and active session management.

<br><br>

#### 8. Admin User Management

<img src="docs/images/gallery/promptvault_admin_user_mgmt.jpg" alt="Admin User Management" width="90%"><br/>
Admin dashboard for user management with filters, role badges, and quick actions.

</div>

</details>

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (for production) or SQLite 3.x (for development)
- Docker and Docker Compose (recommended for production deployment)

### Quick Start with Docker Compose

The fastest way to get started with full database support:

```bash
# Clone repository
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault

# Configure environment
cp .env.example .env
# Edit .env and set POSTGRES_PASSWORD

# Generate JWT signing keys for authentication
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem

# Update .env with JWT key paths
echo "JWT_PRIVATE_KEY_PATH=$(pwd)/es256-private.pem" >> .env
echo "JWT_PUBLIC_KEY_PATH=$(pwd)/es256-public.pem" >> .env

# Start services (PostgreSQL + PromptVault)
docker-compose up -d

# Run database migrations
docker-compose exec web alembic upgrade head

# Create default admin user
docker-compose exec web python scripts/create_admin_user.py

# (Optional) Migrate existing JSON data
docker-compose exec web python scripts/migrate_json_to_db.py
```

Then open your browser to `http://localhost:8001` and login with your admin credentials.

### Additional Installation Options

For detailed deployment instructions including manual installation, environment configuration, and production setup, see:

- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete deployment instructions for Docker, Docker Compose, and manual deployment
- **[Authentication Deployment Guide](docs/AUTHENTICATION_DEPLOYMENT.md)** - Authentication setup with JWT key generation
- **[Migration Guide](docs/MIGRATION_GUIDE.md)** - Step-by-step guide for migrating from JSON to database storage
- **[Database Specification](docs/SPECS/SPEC_DATABASE.md)** - Technical specification and architecture details

## Authentication

PromptVault includes a comprehensive authentication and authorization system with JWT tokens and role-based access control (RBAC), making it production-ready for multi-user deployments.

### User Roles

PromptVault supports three distinct user roles with different permission levels:

- **Viewer**: Read-only access to own prompts. Can view and export prompts but cannot create, edit, or delete. Ideal for stakeholders who need to review prompts without making changes.

- **Editor**: Full access to own prompts including create, read, update, and delete operations. Can manage categories, tags, use version control, and perform import/export. This is the standard role for content creators.

- **Admin**: All editor permissions plus user management capabilities. Can view, edit, and delete any user's prompts, manage user accounts, assign roles, and access system-wide features like backups and audit logs. Required for system administration.

### Security Features

PromptVault implements defense-in-depth security following OWASP best practices:

**Password Security:**

- Argon2id password hashing (winner of Password Hashing Competition, OWASP recommended)
- Password policy enforcement: minimum 12 characters with complexity requirements
- Common password detection to prevent easily guessable passwords
- Account lockout after 5 failed login attempts (15-minute duration)

**Token-Based Authentication:**

- ES256 (ECDSA P-256) JWT tokens for secure authentication
- Short-lived access tokens (30 minutes) with automatic refresh
- Refresh token rotation on every use for enhanced security
- Token family tracking with automatic reuse detection and revocation
- HTTP-only cookies to prevent XSS attacks

**Rate Limiting & Protection:**

- Rate limiting on authentication endpoints (slowapi + Redis)
- Failed login attempt tracking per user
- Temporary account lockout after repeated failures
- CSRF protection via SameSite=Strict cookies

**Session Management:**

- Maximum 5 concurrent sessions per user
- Session metadata tracking (device, browser, IP, last used)
- Ability to view and revoke active sessions
- Automatic cleanup of expired sessions

**Password Reset Flow:**

- Secure email-based password reset with single-use tokens
- 1-hour token expiration for security
- Rate limiting (3 requests per hour per IP)
- No user enumeration (same response for existing/non-existing emails)

### First-Time Setup

After deploying PromptVault, you need to create an admin user to access the system:

```bash
# If using Docker Compose
docker-compose exec web python scripts/create_admin_user.py

# If running locally
python scripts/create_admin_user.py
```

The script will:

1. Prompt you for admin credentials (username, email, password)
2. Validate password strength and requirements
3. Create the admin user with full permissions
4. Display success confirmation

**Important**: Keep your admin credentials secure and change the password if you suspect it has been compromised.

### Authentication Endpoints

PromptVault provides 20 authentication endpoints organized into three categories:

**Public Endpoints (no authentication required):**

- `POST /api/auth/register` - Create new user account
- `POST /api/auth/login` - Login and receive JWT tokens
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout and revoke tokens
- `POST /api/auth/password-reset/request` - Request password reset email
- `POST /api/auth/password-reset/confirm` - Confirm password reset with token

**Protected User Endpoints (authentication required):**

- `GET /api/auth/me` - Get current user profile
- `PUT /api/auth/me` - Update profile information
- `POST /api/auth/me/change-password` - Change password
- `GET /api/auth/me/sessions` - View active sessions
- `DELETE /api/auth/me/sessions/{session_id}` - Revoke specific session

**Admin Endpoints (admin role required):**

- `GET /api/admin/users` - List all users with pagination
- `GET /api/admin/users/{user_id}` - Get user details
- `PUT /api/admin/users/{user_id}/role` - Update user role
- `PUT /api/admin/users/{user_id}/status` - Activate/deactivate user
- `DELETE /api/admin/users/{user_id}` - Delete user account
- `GET /api/admin/sessions` - View all sessions across all users
- `DELETE /api/admin/sessions/{session_id}` - Revoke any user's session

For complete API documentation with request/response examples, see [Authentication API Guide](docs/AUTHENTICATION_API.md).

For security documentation and OWASP compliance details, see [Authentication Security Guide](docs/AUTHENTICATION_SECURITY.md).

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

By default, the application will run on port 8003. To use a different port, set the `PORT` environment variable:

```bash
PORT=8001 python3 run_web.py
```

3. Open your browser and go to `http://localhost:8003` (or the port you specified)

4. To stop the web application, press `Ctrl+C` in the terminal where the server is running

**Note:** PromptVault is now a web-only application. The legacy desktop version has been deprecated and its startup scripts removed.

### Features

- **Authentication & Authorization**: Multi-user support with JWT tokens, role-based access control (viewer, editor, admin), and session management
- **Prompt Management**: Create, edit, delete, and organize prompts through an intuitive web interface
- **Bulk Operations**: Multi-select prompts with checkboxes and delete multiple prompts in a single operation with automatic backups
- **Version Control**: Git-like versioning system with full history tracking, diff visualization, and safe revert functionality
- **Categories & Tags**: Organize prompts with categories and tags for easy discovery
- **Search & Filter**: Find prompts quickly with advanced filtering and search capabilities
- **Import/Export**: Support for CSV, Markdown, and JSON formats with preview functionality
- **Data Backup System**: Comprehensive backup and restoration with automatic pre-operation backups, manual backups, cleanup, and compression
- **Security**: Argon2id password hashing, ES256 JWT tokens, rate limiting, account lockout, password reset flow
- **Responsive Design**: Modern, mobile-friendly interface that works on all devices
- **Multi-language Support**: Internationalization with English, French, Spanish, and German (authentication UI in English)
- **Validation & Monitoring**: End-to-end validation/sanitization across API, server, and client with `/api/validation/stats` metrics (see below)

### Internationalization

PromptVault supports multiple languages (English, French, Spanish, German). The application will automatically detect your system language, but you can also change languages from the language selector in the header. <!-- TODO: moving language selection into profil -->

**Translation Files:**

- Web interface uses JSON translation files in `src/web/static/locales/`
- Translations are loaded dynamically using i18next

### Validation & Monitoring

PromptVault ships with an end-to-end input validation and sanitization framework:

- **API contracts**: All POST/PUT endpoints use Pydantic schemas with length, pattern, and enum constraints (prompts, export/import, backups, version revert).
- **Server sanitization**: Safe filename/backup handling, upload MIME/size checks, control-character stripping, whitespace normalization, tag deduplication.
- **Client parity**: Real-time validation, character counters, duplicate-tag warnings, ARIA/i18n (en/fr/es/de), suppression of native browser prompts.
- **Monitoring**: Validation metrics persisted to `data/logs/validation_metrics.json` and exposed via `GET /api/validation/stats` (success/failure counts, per-endpoint breakdown, recent failures, failure_rate).

See `docs/API_VALIDATION_AND_MONITORING.md` and `docs/VALIDATION_TEST_CHECKLIST.md` for usage and test steps.

### Project Structure

PromptVault follows a clean, layered architecture:

- **`src/web/`** - FastAPI web application, templates, and static assets
- **`src/services/`** - Business logic layer (data services, filtering, versioning, import/export, backups)
- **`src/db/`** - Database layer with SQLAlchemy models and repositories
- **`scripts/`** - Utility scripts (database migration, operations testing)
- **`alembic/`** - Database migration version control
- **`data/`** - Application data (database, backups, logs)
- **`tests/`** - Comprehensive test suite (509 tests, 86.90% coverage)
- **`docs/`** - Documentation and specifications

For detailed project structure and development guidelines, see [AGENTS.md](docs/AGENTS.md).

## Testing

Testing instructions live in **[docs/TESTING.md](docs/TESTING.md)**, including backend (pytest) and frontend (Vitest) commands, coverage thresholds, and CI guidance.

## Observability & Telemetry

- **Structured Logs**: Application and audit logs live in `data/logs/` as newline-delimited JSON. Use tools like `jq` (`tail -f data/logs/audit.log | jq '.action,.resource_id'`) when troubleshooting in development.
- **Frontend Reporter**: `src/web/static/js/telemetry.js` registers a global `window.FrontendLogger`. Call `window.FrontendLogger.reportError('component', 'action', error, { extra: 'context' });` to capture handled failures. All payloads are sanitized (strings truncated to 500–2,000 chars) and rate limited (10 reports per client IP per minute).
- **Opt-out Controls**: Developers/testers can disable reporting via `window.FrontendLogger.disable()` or by setting `localStorage.setItem('promptvault.telemetry.optOut', 'true')`. Call `window.FrontendLogger.enable()` to re-enable. The reporter only sends when enabled and still logs to the browser console for debugging.
- **Server Endpoint**: The `/api/logs/frontend` route receives telemetry, enriches it with the caller IP/request metadata, and stores it through the same logging infrastructure so alerts/exports see both backend and frontend failures.

## Roadmap

For a comprehensive feature improvement roadmap with detailed implementation plans, see [ROADMAP.md](ROADMAP.md).

### Completed Features

- [x] **Version Control System:** Git-like versioning with history tracking, diff visualization, and revert functionality
- [x] **Search & Filtering:** Advanced searching and filtering capabilities across all prompts
- [x] **Data Backup System:** Comprehensive backup and restoration with automatic pre-operation backups, manual backups, cleanup, and compression
- [x] **Unit Tests:** Comprehensive test coverage (85%+) for core functionality with performance benchmarks
- [x] **Database Migration:** Complete transition from JSON to SQLite/PostgreSQL with backward compatibility (see [Migration Guide](docs/MIGRATION_GUIDE.md))
- [x] **Docker & Deployment:** Production-ready Docker setup with PostgreSQL integration and health checks (see [Deployment Guide](docs/DEPLOYMENT.md))
- [x] **Authentication & Authorization:** Multi-user JWT authentication with role-based access control (viewer, editor, admin), Argon2id password hashing, ES256 tokens, session management, password reset flow, and 481 passing tests with 99.8% coverage (see [Authentication Guide](docs/AUTHENTICATION_DEPLOYMENT.md))

### Phase 1: Foundation Strengthening (Priority: High)

- [x] **Input Validation & Sanitization:** Comprehensive validation framework preventing injection attacks and ensuring data integrity
- [x] **Error Handling & Logging:** Centralized logging infrastructure with structured logs and audit trails
- [x] **Database Backend:** SQLAlchemy ORM with repository pattern, Alembic migrations, and PostgreSQL/SQLite support
- [ ] **Performance Monitoring:** Real-time monitoring with APM, error tracking, and analytics dashboards
- [ ] **Accessibility Compliance:** WCAG 2.1 AA compliance with full keyboard navigation and screen reader support

### Phase 2: Security & Architecture (Priority: High)

- [x] **Authentication & Authorization:** User management with JWT tokens and role-based access control (COMPLETED)
- [x] **TypeScript Migration:** Convert frontend to TypeScript for type safety and better developer experience
- [ ] **API Documentation:** Interactive OpenAPI/Swagger documentation with client SDKs
- [ ] **Full-Text Search:** PostgreSQL FTS for advanced search capabilities with ranking and relevance scoring

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

This project is licensed under the **MPL 2.0 license**.

See [LICENSE](LICENSE) for more information.

## Disclaimer – Vibe coding & AI assistance

This repository was developed using a *vibe coding* approach, with assistance from AI tools.

The code was written iteratively, with human review, testing, and decision-making at each step.  
AI assistance was used to accelerate ideation, refactoring, and documentation, but responsibility for the design choices, validation, and final output remains entirely human.

Transparency matters: this project reflects a human–AI collaborative workflow.

## Acknowledgements

- Repository files templates provided by [dec0dOS/amazing-github-template](https://github.com/dec0dOS/amazing-github-template)
- Repository icon: [Reading icons created by Freepik - Flaticon](https://www.flaticon.com/free-icons/reading)
