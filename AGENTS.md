# AGENTS.md

This file provides guidance to any coding agent when working with code in this repository. Repository is hosted on on [Codeberg](https://codeberg.org/medenor/promptvault.git) (not GitHub).

## Overview

PromptVault is a modern web-based prompt management application built with FastAPI. It provides a responsive interface for organizing, versioning, and managing AI prompts with features including Git-like version control, comprehensive backup systems, and multi-language support. The application uses a modular service-oriented architecture with clear separation between business logic, web layer, and data persistence.

## Development Commands

### Build & Development

- **Run Development Server**: `python run_web.py` (default port 8003)
- **Run with Custom Port**: `PORT=8001 python run_web.py`
- **Run with Docker**: `docker-compose up --build` (production, port 8001)
- **NEVER manually start uvicorn** - Always use the provided startup scripts
- **Frontend Dev Server**: `npm run dev` (Vite, default port 5173)

### Code Quality

- **Format Code**: Use black code formatter (configured in project)
- **Python Version**: Python 3.14+ minimum (required for database features)
- **Before Commits**: Run full test suite and ensure coverage meets 85% threshold
- **Frontend Lint**: `npm run lint` (ESLint) and `npm run format` (Prettier)
- **Frontend Typecheck**: `npm run typecheck`
- **Type-safe i18n**: Use `t('key.path')` with `TranslationKey` for compile-time safety. Use `tUnsafe()` only for dynamic keys (e.g. `data-i18n` attributes).
- **Locale Sources**: Translation keys live in `src/web/static/locales/*.json` (TypeScript keys inferred from `en.json`).

### Git Workflow

- **Always work on a branch**: Never commit non-trivial changes directly to `main`. Create a feature/fix branch, push it, and open a PR on Codeberg (see `.forgejo/PULL_REQUEST_TEMPLATE.md`) — even for solo work, so changes go through review and CI.
- **Docs-only exception**: Small, low-risk documentation-only updates (e.g. marking a roadmap item done, changelog entries for already-merged work) may be committed directly to `main` if the user explicitly says so for that change; otherwise default to a branch + PR.
- **Read-only tasks stay read-only**: If a task is scoped as investigation/diagnosis only (e.g. "root-cause this failure," "find out why," any task explicitly marked read-only or "do not fix/modify"), do not commit, push, branch, or open a PR — report findings back and let the requester decide on any fix. Never open a PR, merge, push, or otherwise write to the remote without an explicit go-ahead for that specific action; being told to "investigate" or "look into" something is not authorization to also fix and publish it. This applies to subagents/forks too — a delegated read-only task must not escalate into a write action on its own.

### Testing

> **Important:** Always use `python3 -m pytest` instead of `pytest` directly to ensure correct dependency versions.

- **Run Full Test Suite**: `python3 -m pytest` (includes coverage reporting, ~70 seconds)
- **Run Repository Tests**: `python3 -m pytest tests/test_db_repositories.py`
- **Run Service Tests**: `python3 -m pytest tests/test_db_services.py`
- **Run Version Control Tests**: `python3 -m pytest tests/test_version_system.py`
- **Run API Tests**: `python3 -m pytest tests/test_web_api.py`
- **Run Admin Tests**: `python3 -m pytest tests/test_admin_api.py`
- **Coverage Report**: Generated in `htmlcov/index.html` after running pytest
- **Coverage Threshold**: 85% minimum (enforced in pytest.ini)
- **Current Backend Coverage**: 83.54% (1087 passing tests, 100% pass rate)
- **Test Documentation**: See `docs/TESTING.md` for comprehensive guide
- **Frontend Unit Tests**: `npm run test:unit` (Vitest)
- **Frontend Coverage**: `npm run test:unit:coverage` (Vitest + v8) - Currently 89.83% (49 tests passing)

## High-Level Architecture

### Core Systems

1. **Database Layer** ([`src/db/`](src/db/))
   - **Database Models** ([`models.py`](src/db/models.py)): SQLAlchemy ORM models
     - `Prompt`: Main prompt entity with relationships
     - `PromptVersion`: Git-like version snapshots
     - `Category`: Prompt categorization
     - `Tag`: Tagging system with many-to-many relationships
     - `User`: User entity for authorship tracking
     - `Backup`: Backup metadata tracking

   - **Repositories** ([`repositories/`](src/db/repositories/)): Data access layer
     - **PromptRepository**: CRUD operations, search, filtering, pagination
     - **VersionRepository**: Version history, comparison, revert operations
     - **CategoryRepository**: Category management with usage tracking
     - **TagRepository**: Tag management, bulk operations, popular tags

   - **Database Configuration** ([`config.py`](src/db/config.py)): Database setup
     - PostgreSQL support (production)
     - SQLite support (development)
     - Environment-based configuration
     - Connection pooling and session management

2. **Service Layer** ([`src/services/`](src/services/))
   - **PromptDataServiceDB** ([`prompt_data_service_db.py`](src/services/prompt_data_service_db.py)): Core data operations
     - Handles all CRUD operations for prompts
     - Database-backed persistence with transactions
     - Automatic versioning on updates
     - Category and tag management
     - Search and filtering capabilities

   - **BackupServiceDB** ([`backup_service_db.py`](src/services/backup_service_db.py)): Database backup system
     - SQLite: File copy with metadata tracking
     - PostgreSQL: pg_dump integration
     - Backup restoration with safety features
     - Retention policies and cleanup
     - Compression for older backups

   - **PromptImportExportService** ([`prompt_import_export_service.py`](src/services/prompt_import_export_service.py)): Data import/export
     - CSV format support
     - Markdown format support
     - JSON format support
     - Multiple import modes (append, merge, replace)
     - Data validation on import

3. **Web Application Layer** ([`src/web/`](src/web/))
   - **FastAPI Application** ([`app.py`](src/web/app.py)): Main web server
     - RESTful API endpoints
     - Jinja2 template rendering
     - Static file serving
     - Service coordination and dependency injection
     - Error handling and logging

   - **Templates** ([`templates/`](src/web/templates/)): Server-side HTML rendering
     - [`index.html`](src/web/templates/index.html): Main application interface
     - [`import_export.html`](src/web/templates/import_export.html): Import/export management page
     - [`backup_management.html`](src/web/templates/backup_management.html): Backup management interface

   - **Static Assets** ([`static/`](src/web/static/)):
     - **TypeScript** ([`ts/`](src/web/static/ts/)): Client-side application logic (active source)
       - [`app.ts`](src/web/static/ts/app.ts): Main UI logic and API interactions
       - [`import-export.ts`](src/web/static/ts/import-export.ts): Import/export functionality
       - [`backup-management.ts`](src/web/static/ts/backup-management.ts): Backup management UI
       - [`components/`](src/web/static/ts/components/): Reusable component system
         - Button, Card, Input, Form, Modal, Layout, Navigation components
         - Type-safe component utilities with full TypeScript support
     - **CSS** ([`css/`](src/web/static/css/)): Tailwind CSS-based styling
       - [`tailwind-globals.css`](src/web/static/css/tailwind-globals.css): Global styles and base configuration
       - [`tailwind.config.ts`](tailwind.config.ts): Design tokens and configuration
     - **i18n** ([`locales/`](src/web/static/locales/)): Translation files (en, fr, es, de)

4. **Data Storage**
   - **Primary Data Store**: Database (SQLite or PostgreSQL)
     - **SQLite**: `data/prompts.db` (development and default)
     - **PostgreSQL**: Configured via `DATABASE_URL` environment variable (production)

   - **Database Schema**:
     - `users`: User accounts with username and email
     - `categories`: Prompt categories with usage tracking
     - `tags`: Global tag definitions
     - `prompts`: Main prompt entities with title, content, note, favorite status
     - `prompt_tags`: Many-to-many relationship between prompts and tags
     - `prompt_versions`: Git-like version snapshots with parent relationships
     - `backups`: Backup metadata tracking

   - **Legacy Data Store**: `data/prompts_data.json` (deprecated, kept for migration)

   - **Backup Storage**:
     - SQLite: `data/backups/` (database file copies + metadata)
     - PostgreSQL: `data/backups/` (pg_dump SQL files + metadata)

   - **Logs**: `data/logs/` (application and audit logs)

### API Endpoints

#### Prompt Management

- `GET /api/prompts` - List all prompts
- `POST /api/prompts` - Create new prompt
- `GET /api/prompts/{id}` - Get specific prompt
- `PUT /api/prompts/{id}` - Update prompt (creates new version)
- `DELETE /api/prompts/{id}` - Delete prompt
- `GET /api/prompts/search` - Search with filters
- `PUT /api/prompts/{id}/favorite` - Toggle favorite status

#### Categorization

- `GET /api/categories` - List all categories
- `GET /api/tags` - List all tags

#### Version Control

- `GET /api/prompts/{id}/versions` - Get version history
- `GET /api/prompts/{id}/versions/compare` - Compare versions
- `GET /api/prompts/{id}/versions/{version_id}` - Get specific version
- `POST /api/prompts/{id}/versions/{version_id}/revert` - Revert to version

#### Import/Export

- `GET /import-export` - Management page
- `POST /api/export` - Export prompts (CSV/Markdown/JSON)
- `POST /api/import` - Import prompts
- `GET /api/import-export/stats` - Import/export statistics

#### Backup Management

- `GET /backup-management` - Management page
- `GET /api/backups` - List all backups
- `POST /api/backups` - Create backup
- `POST /api/backups/{id}/restore` - Restore backup
- `DELETE /api/backups/{id}` - Delete backup
- `POST /api/backups/cleanup` - Cleanup old backups
- `POST /api/backups/compress` - Compress old backups
- `GET /api/backups/stats` - Backup statistics

#### Page Routes

- `GET /` - Main application interface
- `GET /import-export` - Import/export interface
- `GET /backup-management` - Backup management interface

### Key Patterns

- **Service-Oriented Architecture**: Clear separation between data, business logic, and presentation layers
- **RESTful Design**: All operations follow REST principles with proper HTTP methods
- **Factory Pattern**: Service instances created and injected into web application
- **Error Handling**: Try-catch blocks with proper error logging and user-friendly messages
- **Data Validation**: Input validation at both client and server levels
- **Async Operations**: FastAPI async support for file operations (aiofiles)
- **Event-Driven UI**: JavaScript event handlers for real-time updates
- **i18n Support**: Internationalization with i18next library
- **Accessibility**: WCAG 2.1 Level AA compliant UI

## Code Style Guidelines

### MAJOR PRINCIPLES

- **WRITE CLEAN, MAINTAINABLE CODE**: Prioritize readability and maintainability over cleverness
- **FOLLOW EXISTING PATTERNS**: Match the established code style and architecture patterns in the repository
- **SERVICE LAYER FIRST**: All business logic belongs in service classes, not in web routes
- **NO HARDCODING**: Use configuration files, environment variables, or constants for configurable values
- **DEFENSIVE PROGRAMMING**: Always validate inputs and handle edge cases gracefully
- **DOCUMENTATION**: All public methods must have docstrings with Args, Returns, and Raises sections

### Python

- **Type Hints**: Use type hints for all function signatures

  ```python
  def get_prompt(self, prompt_id: int) -> Dict[str, Any]:
  ```

- **Docstrings**: Google-style docstrings for all classes and public methods

  ```python
  def save_prompts(self) -> bool:
      """
      Save prompts to the data file.

      Returns:
          bool: True if successful, False otherwise
      """
  ```

- **Error Handling**: Always use try-except blocks for I/O operations and external calls
- **Naming Conventions**:
  - `snake_case` for functions, methods, and variables
  - `PascalCase` for class names
  - `UPPER_SNAKE_CASE` for constants
- **Imports**: Organize imports in three groups:
  1. Standard library
  2. Third-party packages
  3. Local application imports

### TypeScript (Primary Frontend Language)

The entire frontend has been migrated to TypeScript for type safety and better developer experience.

- **Type Annotations**: Always use explicit type annotations for function parameters and return types

  ```typescript
  function getUserSessions(userId: number): Promise<SessionResponse[]> {
    return fetch(`/api/sessions/${userId}`).then((r) => r.json());
  }
  ```

- **Type Safety**: Leverage TypeScript's type system to catch bugs at compile time
  - Use `TranslationKey` type for i18n keys (compile-time validation)
  - Use union types for state management: `type NotificationType = 'info' | 'success' | 'warning' | 'error'`
  - Export interfaces from service modules for type reuse

  ```typescript
  // services/api.ts
  export interface SessionResponse {
    id: string;
    family_id: string;
    user_agent: string;
    ip_address: string;
    is_current: boolean;
    created_at: string;
    last_used_at: string;
    expires_at: string;
  }
  ```

- **Component Types**: All UI components must export their props interface

  ```typescript
  export interface ButtonProps {
    onClick?: (e: MouseEvent) => void;
    disabled?: boolean;
    className?: string;
    variant?: 'primary' | 'secondary';
  }
  ```

- **Async Operations**: Use async/await with proper error handling and TypeScript generics

  ```typescript
  async function importData<T>(file: File): Promise<ImportResult<T>> {
    try {
      const data = await parseFile(file);
      return { success: true, data };
    } catch (error) {
      reportError('import', 'parse', error);
      throw error;
    }
  }
  ```

- **DOM Manipulation**: Use TypeScript for DOM queries with proper type casting

  ```typescript
  const element = document.getElementById('modal') as HTMLDivElement;
  const input = element.querySelector('input[type="text"]') as HTMLInputElement;
  ```

- **Testing**: All TypeScript files must have corresponding `.test.ts` files using Vitest
  - Use Vitest for unit tests (fast, Vite-native)
  - Mock external dependencies with `vi.mock()`
  - Test at 85%+ coverage per module

- **TypeScript-only frontend**:
  - All frontend source is TypeScript in `static/ts/`
  - Use `noImplicitAny: true` in `tsconfig.json` to enforce type safety
### HTML/Jinja2

- **Semantic HTML**: Use proper HTML5 semantic elements
- **Accessibility**: Include ARIA labels and proper form structure
- **Template Inheritance**: Use Jinja2 template inheritance for consistency
- **Variable Interpolation**: Use `{{ variable }}` for safe HTML escaping

### CSS - Tailwind CSS v4

The project uses **Tailwind CSS v4** for all styling. Do not write custom CSS unless absolutely necessary.

- **Utility-First Approach**: Use Tailwind utility classes instead of writing custom CSS
  - Examples: `bg-blue-500`, `text-lg`, `p-4`, `rounded-lg`, `shadow-md`
  - Compose complex UIs from single-purpose utility classes
  - Never create custom classes unless it's a shared component style

  ```html
  <!-- Good: Using utility classes -->
  <div class="flex items-center justify-between bg-white p-4 rounded-lg shadow-md">
    <h2 class="text-lg font-semibold text-gray-900">Title</h2>
    <button class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">Action</button>
  </div>

  <!-- Bad: Writing custom CSS -->
  <div class="custom-card">
    <h2>Title</h2>
    <button>Action</button>
  </div>
  ```

- **Responsive Design**: Mobile-first with Tailwind breakpoints (`sm`, `md`, `lg`, `xl`, `2xl`)

  ```html
  <!-- Stack vertically on mobile, horizontally on medium+ screens -->
  <div class="flex flex-col md:flex-row gap-4">
    <div class="w-full md:w-1/2">Content</div>
    <div class="w-full md:w-1/2">Sidebar</div>
  </div>
  ```

- **Design Tokens**: Configuration in [`tailwind.config.ts`](tailwind.config.ts) defines all colors, spacing, fonts

  ```typescript
  // tailwind.config.ts
  export default {
    theme: {
      colors: {
        primary: 'var(--color-primary)',
        secondary: 'var(--color-secondary)',
      },
      spacing: {
        xs: 'var(--spacing-xs)',
        sm: 'var(--spacing-sm)',
      },
    },
  };
  ```

- **Global Styles**: Common styles in [`tailwind-globals.css`](src/web/static/css/tailwind-globals.css)
  - Base element defaults (buttons, inputs, forms)
  - Utility extensions
  - Component base classes (only when needed for shared patterns)
  - Do NOT use @layer components for one-off styles (use inline utilities instead)

- **Color System**: Use semantic Tailwind colors with optional custom palette
  - Standard: `blue`, `red`, `gray`, `green`, `yellow`
  - Custom: Define in `tailwind.config.ts` if project-specific colors needed
  - Dark mode: Prefix with `dark:` for dark theme styles

  ```html
  <!-- Light mode (default) -->
  <div class="bg-gray-50 text-gray-900">Light content</div>

  <!-- Dark mode variant -->
  <div class="bg-gray-900 dark:bg-gray-800 text-gray-900 dark:text-gray-100">Content</div>
  ```

- **State Variants**: Tailwind provides built-in state utilities
  - Hover: `hover:bg-blue-600`
  - Focus: `focus:outline-blue-500` (note: use `focus-visible` for keyboard focus only)
  - Active: `active:scale-95`
  - Disabled: `disabled:opacity-50`
  - Group hover: `group-hover:text-blue-500`

- **Component Library**: Reusable components in [`static/ts/components/`](src/web/static/ts/components/)
  - Button, Card, Input, Form, Modal, Layout components
  - These provide consistent styling across the application
  - Always use existing components before creating new ones

- **Custom CSS**: Only write custom CSS in special cases
  - Animation definitions (in global.css with `@keyframes`)
  - Complex layout patterns that can't use flexbox/grid
  - Always document why custom CSS was needed
  - Example: `@keyframes fadeIn { ... }` then use `animate-fadeIn`

- **Avoid**: Don't use inline styles or write custom CSS for simple styling tasks
  - Use Tailwind utilities instead of `style="color: red"`
  - Don't create custom classes for simple styling

### CSS File Consolidation & Cleanup

As part of the Tailwind CSS v4 migration, legacy CSS files should be consolidated:

**Files to Consolidate** (can be removed or merged into `tailwind-globals.css`):

- `/src/web/static/css/style.css` - Legacy component styles (replace with Tailwind utilities + component system)
- `/src/web/static/css/auth.css` - Authentication page styles (migrate to Tailwind utilities)
- `/src/web/static/css/admin.css` - Admin page styles (migrate to Tailwind utilities)
- `/src/web/static/css/sessions.css` - Sessions page styles (migrate to Tailwind utilities)
- `/src/web/static/css/validation.css` - Validation styles (replace with Tailwind utilities)

**Migration Strategy**:

1. Identify any critical styling rules that aren't representable in Tailwind
2. Move those rules to `tailwind-globals.css` with `@layer` directives (only if necessary)
3. Update HTML templates to use Tailwind utility classes
4. Update component implementations to use Tailwind utilities
5. Remove legacy CSS files after verification

**Example**: Converting `auth.css` login form styles

```css
/* Old: auth.css */
.login-form {
  max-width: 400px;
  margin: 0 auto;
  padding: 2rem;
  border-radius: 8px;
  background: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* New: Use Tailwind utilities in template or component */
<div class="max-w-sm mx-auto p-8 rounded-lg bg-white shadow-sm">
  <!-- form content -->
</div>
```

**No custom CSS needed** - Pure Tailwind utilities handle all styling

### General

- **DRY Principle**: Don't Repeat Yourself - extract common logic into reusable functions
- **KISS Principle**: Keep It Simple, Stupid - prefer simple solutions over complex ones
- **Single Responsibility**: Each function/class should have one clear purpose
- **Code Organization**: Group related functionality together in modules
- **Constants**: Define magic numbers and strings as named constants
- **Logging**: All code uses centralized structured logging (`logging_service.get_logger(__name__)`) with JSON payloads, request IDs, and rotating files in `data/logs/`. Reference `docs/plan_centralized_error_logging.md` for the mandated fields and retention targets. `print()` is disallowed in `src/` and `run_web.py`, enforced by the `make lint` CI gate (`rg "print\(" src run_web.py`).

### Observability Requirements (Issue #10)

- **Structured Output**: Application logs (`data/logs/app.log`) and audit logs (`data/logs/audit.log`) must emit JSON objects containing `timestamp`, `level`, `event`, `request_id`, `actor`, `action`, `resource_id`, `status`, and `duration_ms`. Avoid logging prompt or note bodies—stick to metadata.
- **Request Correlation**: Each FastAPI request must receive a request ID (UUIDv4 hex) propagated via `contextvars` into all services and included in every downstream log event.
- **Retention & Rotation**: Target five 10 MB app log files (~2 weeks) and ten 5 MB audit files (~30 days). The `./data` host volume (mounted as `/app/data` in Docker) already persists logs; no extra volume is required, but operators need to copy `data/logs/` if they want log backups.
- **Audit Coverage**: Emit audit entries for prompt CRUD, version reverts, import/export actions, backup lifecycle events, cleanup/compression operations, and any automated intervention (auto backups before deletes/imports). Include actor identity (`getpass.getuser()` until auth ships) and outcome (`success`, `failure`).
- **Configurability**: Support `LOG_LEVEL` and `AUDIT_LOG_LEVEL` env vars (default `INFO`) plus developer-friendly console formatting when `ENVIRONMENT=development`. Provide documentation in README/AGENTS describing the knobs.
- **Health Signals**: ValidationMonitor write failures, frontend error reports, and logging subsystem issues must be logged through the structured logger so ops teams can alert on them.

## Component System Development

The frontend uses a modular, type-safe component system built with TypeScript and styled with Tailwind CSS.

### Component Location and Structure

All components are located in [`src/web/static/ts/components/`](src/web/static/ts/components/):

```
components/
├── Button.ts          # Button component
├── Card.ts            # Card/container component
├── Input.ts           # Input field component
├── Form.ts            # Form wrapper component
├── Modal.ts           # Modal dialog component
├── Layout.ts          # Layout primitives
└── Navigation.ts      # Navigation component
```

### Creating New Components

Follow this pattern when creating new components:

```typescript
// src/web/static/ts/components/MyComponent.ts

/**
 * Props interface must be exported for type safety
 */
export interface MyComponentProps {
  title: string;
  onClick?: (event: MouseEvent) => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
  className?: string;
}

/**
 * Component factory function - returns a DOM element
 * All styling must use Tailwind utility classes
 */
export function MyComponent(props: MyComponentProps): HTMLElement {
  const container = document.createElement('div');
  container.className = `
    flex items-center justify-between
    bg-white p-4 rounded-lg shadow-md
    ${props.disabled ? 'opacity-50 cursor-not-allowed' : ''}
    ${props.className || ''}
  `
    .trim()
    .replace(/\s+/g, ' ');

  const title = document.createElement('h3');
  title.className = 'text-lg font-semibold text-gray-900';
  title.textContent = props.title;

  if (props.onClick) {
    container.addEventListener('click', props.onClick);
  }

  container.appendChild(title);
  return container;
}
```

### Component Best Practices

1. **Exports**: Always export the Props interface and component function

   ```typescript
   export interface ButtonProps { ... }
   export function Button(props: ButtonProps): HTMLElement { ... }
   ```

2. **Styling**: Use Tailwind utilities exclusively, no custom CSS
   - Build class strings with template literals
   - Use conditional utility classes for state variants
   - Compose utilities for complex layouts

3. **Event Handlers**: Accept callbacks as optional props
   - Always use strong typing: `onClick?: (event: MouseEvent) => void`
   - Attach listeners with `addEventListener()`
   - Clean up listeners when components are removed

4. **Accessibility**: Include ARIA attributes where appropriate

   ```typescript
   button.setAttribute('aria-label', props.ariaLabel || 'Action');
   button.setAttribute('role', 'button');
   ```

5. **Testability**: Design components for easy testing
   - Keep logic simple and separated
   - Use predictable class names
   - Export interfaces for test type checking

### Using Components

Components should be used with proper type checking:

```typescript
import { Button, type ButtonProps } from '@/components/Button';

// Create a button with type-safe props
const button = Button({
  title: 'Submit',
  onClick: (e) => console.log('Clicked'),
  variant: 'primary',
  className: 'mt-4',
});

document.body.appendChild(button);
```

### Component Testing

Each component must have a corresponding test file:

```typescript
// src/web/static/ts/components/__tests__/MyComponent.test.ts

import { describe, it, expect, vi } from 'vitest';
import { MyComponent, type MyComponentProps } from '@/components/MyComponent';

describe('MyComponent', () => {
  it('renders with provided title', () => {
    const element = MyComponent({ title: 'Test Title' });
    expect(element.textContent).toContain('Test Title');
  });

  it('calls onClick handler when clicked', () => {
    const onClick = vi.fn();
    const element = MyComponent({ title: 'Test', onClick });
    element.click();
    expect(onClick).toHaveBeenCalled();
  });

  it('applies Tailwind classes correctly', () => {
    const element = MyComponent({ title: 'Test' });
    expect(element.className).toContain('flex');
    expect(element.className).toContain('bg-white');
  });
});
```

### Avoiding Common Mistakes

- ❌ Don't use `innerHTML` directly (XSS vulnerability)
- ❌ Don't write custom CSS classes (use Tailwind utilities)
- ❌ Don't forget to type component props
- ❌ Don't hardcode strings (use i18n for UI text)
- ✅ Do use `document.createElement()` and `appendChild()`
- ✅ Do compose utilities for styling
- ✅ Do test all components at 85%+ coverage
- ✅ Do handle edge cases and null values

## Testing Guidelines

### Test Organization

- **Location**: All tests in [`tests/`](tests/) directory
- **Fixtures**: Shared fixtures in [`conftest.py`](tests/conftest.py)
- **Naming**: Test files must start with `test_` (e.g., `test_db_services.py`)
- **Structure**: One test file per service/module being tested

### Test Fixtures

Available in [`conftest.py`](tests/conftest.py):

- **Database Fixtures**:
  - `test_db_engine` - In-memory SQLite engine for fast, isolated tests
  - `test_db_session` - Database session with automatic rollback
  - `reset_database` - Smart database reset (autouse, backward compatible)

- **Model Fixtures**:
  - `test_user` - Test user for authorship tracking
  - `test_category` - Test category with unique name
  - `test_tags` - List of test tags
  - `test_prompt` - Single prompt with relationships
  - `test_prompt_with_versions` - Prompt with 10 versions for history testing

- **Repository Fixtures**:
  - `prompt_repo` - PromptRepository instance
  - `version_repo` - VersionRepository instance
  - `category_repo` - CategoryRepository instance
  - `tag_repo` - TagRepository instance

- **Service Fixtures**:
  - `db_data_service` - Database-backed PromptDataService
  - `db_backup_service` - Database-backed BackupService
  - `sample_prompt_data` - Factory for creating test prompt data

- **API Testing**:
  - `api_client` - FastAPI TestClient with database backend
  - `api_client_context` - Isolated test client with temporary data

- **Legacy Fixtures** (for backward compatibility):
  - `empty_data_service`, `populated_data_service` - JSON-based services (deprecated)
  - `sample_csv_content`, `sample_markdown_content` - Import/export test data

### Test Suite Structure

**See [`docs/TESTING.md`](docs/TESTING.md) for comprehensive testing documentation.**

1. **Repository Tests** ([`test_db_repositories.py`](tests/test_db_repositories.py)): 78 tests, 89-100% coverage
   - PromptRepository CRUD operations, search, filtering, pagination
   - VersionRepository history, comparison, revert operations
   - CategoryRepository management with usage tracking
   - TagRepository bulk operations and popular tags

2. **Service Tests** ([`test_db_services.py`](tests/test_db_services.py)): 88 tests, 94% pass rate
   - PromptDataService with database backend
   - BackupService for SQLite and PostgreSQL

3. **Version Control Tests** ([`test_version_system.py`](tests/test_version_system.py)): 48 tests, 95-100% coverage
   - Version creation and history tracking
   - Version comparison and diff generation
   - Version revert operations
   - Integration workflows

4. **API Endpoint Tests** ([`test_web_api.py`](tests/test_web_api.py)): API integration tests
   - RESTful endpoints for prompts, categories, tags
   - Version control endpoints
   - Import/export functionality
   - Backup management

### Test Coverage Metrics

- **Overall Coverage**: 86.90% (exceeds 85% threshold)
- **Total Tests**: 509 passing out of 514 (99% pass rate)
- **Execution Time**: ~8 seconds (13x faster than legacy suite)
- **Test Infrastructure**: 30 comprehensive fixtures supporting database-backed testing

### Writing Tests

Database-backed test example:

```python
def test_add_prompt(db_data_service, sample_prompt_data):
    """Test adding a new prompt with database backend."""
    # Arrange
    prompt_data = sample_prompt_data(title="New Prompt")

    # Act
    prompt_id = db_data_service.add_new_prompt(prompt_data)

    # Assert
    assert prompt_id is not None
    prompt = db_data_service.get_prompt_by_id(prompt_id)
    assert prompt['title'] == "New Prompt"

    # Verify version created
    versions = db_data_service.get_prompt_versions(prompt_id)
    assert len(versions) == 1
    assert versions[0]['message'] == "Initial version"
```

## Development Session Planning

### Session Workflow

When working on a development session:

1. **Understand the Request**: Carefully read and analyze the user's requirements
2. **Explore the Codebase**: Use Read, Grep, and Glob tools to understand existing implementation
3. **Plan Your Approach**: Consider impact on existing code and tests
4. **Implement Changes**: Follow established patterns and code style
5. **Update Tests**: Ensure test coverage remains above 85%
6. **Test Your Changes**: Run relevant tests before committing
7. **Document Changes**: Update CHANGELOG.md with user-facing changes
8. **Validation Framework**: Verify client/server validation parity, `/api/validation/stats` monitoring, and keep `docs/API_VALIDATION_AND_MONITORING.md` + `docs/VALIDATION_TEST_CHECKLIST.md` aligned

### Before Making Changes

- **Read Existing Code**: Always read the relevant service/module first
- **Check Tests**: Review existing tests to understand expected behavior
- **Identify Patterns**: Follow established architectural patterns
- **Consider Impact**: Think about downstream effects of changes
- **TypeScript Compatibility**: For frontend changes, ensure TypeScript compilation passes with `npm run typecheck`
- **Tailwind CSS Compliance**: Review component styling to ensure Tailwind utilities are used exclusively

### After Making Changes

- **Run Tests**: `python3 -m pytest` to ensure all tests pass
- **Check Coverage**: Verify coverage remains ≥ 85%
- **Update Documentation**: Update docstrings and comments
- **Verify Functionality**: Manually test the feature if possible
- **TypeScript Build**: For frontend changes, run `npm run build:ts` to verify TypeScript compiles without errors
- **Frontend Tests**: Run `npm run test:unit` to ensure frontend unit tests pass
- **CSS Validation**: Verify Tailwind CSS utility classes are correctly applied with `npm run lint`

## Important Notes

### Data Storage and Migration

- **Current System**: Database-backed (SQLite or PostgreSQL)
- **Database Models**: SQLAlchemy ORM with relationships and constraints
- **Primary Keys**: Integer IDs for prompts, categories, tags, users
- **Version IDs**: UUID strings for reliable version identification
- **Timestamps**: ISO 8601 format stored in database (e.g., "2024-01-01T12:00:00Z")
- **Legacy System**: JSON file storage (deprecated, kept for migration only)
- **Migration Path**: Use database-backed services (PromptDataServiceDB, BackupServiceDB)

### Version Control System

- **Database-Backed**: Version snapshots stored in `prompt_versions` table
- **Git-like Design**: Parent-child relationships, immutable history
- **Automatic Versioning**: Every prompt update creates a new version
- **Immutable History**: Version history is never lost, only extended
- **Revert Creates New Version**: Reverting doesn't delete history, creates new commit
- **Metadata Required**: Each version has timestamp, author, message, and full data snapshot
- **Version Comparison**: Built-in diff generation for comparing versions

### Backup System

- **Database-Specific**:
  - **SQLite**: File copy with metadata tracking in `backups` table
  - **PostgreSQL**: pg_dump integration with SQL file storage
- **Pre-operation Backups**: Automatic before risky operations (delete, replace import)
- **Manual Backups**: User can create named backups anytime
- **Pre-restore Backups**: Automatic safety backup before restoring another backup
- **Retention Policy**: Configurable cleanup of old backups
- **Compression**: Older backups automatically compressed with gzip
- **Metadata Tracking**: All backup operations tracked in database

### Internationalization

- **Translation Keys**: All UI strings use i18next translation keys
- **Supported Languages**: English (en), French (fr), Spanish (es), German (de)
- **Translation Files**: JSON files in [`src/web/static/locales/`](src/web/static/locales/)
- **Dynamic Switching**: Users can change language without restarting

### Docker Deployment

- **Data Persistence**: Data directory mounted as volume (`./data:/app/data:rw`)
- **Port Mapping**: 8001 (host) → 8000 (container)
- **Hot Reload**: Enabled in development mode
- **Health Checks**: Container health monitoring configured

### Common Pitfalls

- **Don't modify the web app without updating tests**: Always maintain test coverage
- **Don't hardcode file paths**: Use `os.path.join()` and relative paths
- **Don't skip error handling**: Always wrap I/O and database operations in try-except
- **Don't forget transactions**: Use database sessions with proper commit/rollback
- **Use database-backed services**: PromptDataServiceDB, BackupServiceDB (the legacy JSON-file services have been removed)
- **Don't break database migrations**: Test with both SQLite and PostgreSQL when modifying models — see [docs/DEVELOPMENT.md#writing-alembic-migrations](docs/DEVELOPMENT.md#writing-alembic-migrations) for the dialect-portability rules and a real incident (v1.10.0/v1.10.1) this caught
- **Don't use console.log in production**: Remove debug statements before committing
- **Don't skip database session management**: Always close sessions properly

### Technical Debt and Future Work

See issues tracker at: <https://codeberg.org/medenor/promptvault/issues>

**Completed:**

- ✅ TypeScript migration for frontend (Phase 5-7, 100% complete)
  - All new code written in TypeScript with strict type checking (`noImplicitAny: true`)
  - Legacy JavaScript files preserved but not modified
  - Component system built with type-safe interfaces
  - Test coverage: 89.83% (49 tests, 100% pass rate)
- ✅ Tailwind CSS v4 implementation (Phase 5-7, 100% complete)
  - Entire UI redesigned with Tailwind utility classes
  - Component library with responsive design patterns
  - Design token system with custom theme configuration
  - Dark mode support ready for future implementation

Current priorities:

- Input validation and sanitization
- Centralized error handling and logging (Issue #10)
- Tag and category management interface
- PostgreSQL production deployment guide

## Quick Reference

### Running the Application

```bash
# Development
python run_web.py

# Custom port
PORT=8001 python run_web.py

# Docker production
docker-compose up --build
```

### Testing (Quick Reference)

```bash
# Full test suite with coverage (~10 seconds)
# IMPORTANT: Use python3 -m pytest (not pytest directly)
python3 -m pytest

# Repository layer tests
python3 -m pytest tests/test_db_repositories.py

# Service layer tests
python3 -m pytest tests/test_db_services.py

# Version control tests
python3 -m pytest tests/test_version_system.py

# API endpoint tests
python3 -m pytest tests/test_web_api.py

# View coverage report (current: 86.46%)
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# See comprehensive testing guide
cat docs/TESTING.md
```

> **Why `python3 -m pytest`?** This ensures pytest runs with the correct Python environment and dependency versions, avoiding conflicts with globally installed packages like httpx, fastapi, or starlette.

### Project URLs

- **Repository**: <https://codeberg.org/medenor/promptvault>
- **Issues**: <https://codeberg.org/medenor/promptvault/issues>
- **License**: MPL 2.0 (always add the MPL 2.0 header to files)

### Key Files

| File                                                                               | Purpose                                       |
| ---------------------------------------------------------------------------------- | --------------------------------------------- |
| [`run_web.py`](run_web.py)                                                         | Web server startup script                     |
| [`src/web/app.py`](src/web/app.py)                                                 | FastAPI application and routes                |
| [`src/db/models.py`](src/db/models.py)                                             | SQLAlchemy database models                    |
| [`src/db/config.py`](src/db/config.py)                                             | Database configuration and session management |
| [`src/db/repositories/`](src/db/repositories/)                                     | Repository layer (data access)                |
| [`src/services/prompt_data_service_db.py`](src/services/prompt_data_service_db.py) | Database-backed data service                  |
| [`src/services/backup_service_db.py`](src/services/backup_service_db.py)           | Database-backed backup service                |
| [`data/prompts.db`](data/prompts.db)                                               | SQLite database (development)                 |
| [`tests/conftest.py`](tests/conftest.py)                                           | Test fixtures (30 database-aware fixtures)    |
| [`tests/test_db_repositories.py`](tests/test_db_repositories.py)                   | Repository layer tests                        |
| [`tests/test_db_services.py`](tests/test_db_services.py)                           | Service layer tests                           |
| [`tests/test_version_system.py`](tests/test_version_system.py)                     | Version control tests                         |
| [`docs/TESTING.md`](docs/TESTING.md)                                               | Comprehensive testing guide                   |
| [`docs/SPECS/SPEC_DATABASE.md`](docs/SPECS/SPEC_DATABASE.md)                       | Database architecture specification           |
| [`pyproject.toml`](pyproject.toml)                                                 | Project configuration                         |
| [`pytest.ini`](pytest.ini)                                                         | Test configuration                            |
| [`.coveragerc`](.coveragerc)                                                       | Coverage configuration (excludes legacy code) |
| [`Dockerfile`](Dockerfile)                                                         | Container configuration                       |
| [`docker-compose.yml`](docker-compose.yml)                                         | Docker Compose setup                          |
| [`CHANGELOG.md`](CHANGELOG.md)                                                     | Release history                               |

## Summary

PromptVault is a production-ready web application for managing AI prompts with comprehensive version control and backup systems. The application has migrated from JSON file storage to a robust database-backed architecture using SQLAlchemy ORM with support for both SQLite (development) and PostgreSQL (production).

**Key Features:**

- **Database-Backed Architecture**: SQLAlchemy models with repository pattern for data access
- **Git-like Version Control**: Immutable version history with parent-child relationships
- **Comprehensive Backup System**: Database-specific backup strategies for SQLite and PostgreSQL
- **Service-Oriented Design**: Clear separation between repositories, services, and web layer
- **High Test Coverage**: 83.54% backend (1087 tests), 89.83% frontend (49 tests) - 100% pass rate
- **Fast Test Execution**: ~70 seconds full suite using in-memory SQLite for backend, <5 seconds for frontend
- **Modern UI**: Tailwind CSS v4 with responsive design, WCAG 2.1 Level AA accessibility features, and component library
- **Multi-Language Support**: Internationalization for English, French, Spanish, and German
- **Security**: JWT ES256 authentication, Argon2id password hashing, rate limiting, session management
- **Docker Deployment**: Production-ready containerization with data persistence

**Development Guidelines:**

- Use database-backed services (PromptDataServiceDB, BackupServiceDB)
- Maintain 85% test coverage threshold (current: 86.90%)
- Follow repository pattern for data access
- Use proper database session management with transactions
- Test with both SQLite and PostgreSQL when modifying models
- Refer to `docs/TESTING.md` for comprehensive testing guide

When contributing, prioritize code readability, maintainability, and test coverage. Follow the existing architectural patterns and ensure all public APIs have comprehensive documentation.
