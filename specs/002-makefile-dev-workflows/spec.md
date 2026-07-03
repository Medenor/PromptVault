# Feature Specification: Developer Workflow Makefile

**Feature Branch**: `002-makefile-dev-workflows`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "Implement a `Makefile` to streamline development workflows and standardize common tasks. Currently, repetitive commands are run manually, which slows onboarding and development. Proposed targets: `make dev`, `make install`, `make test`, `make lint`, `make build`."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast Onboarding for a New Contributor (Priority: P1)

A developer who has just cloned the repository wants to get the full application running — backend server and live-reloading frontend — without reading multiple documentation pages or memorizing the project's exact port numbers, entry scripts, and dependency managers. They run a single install command followed by a single dev command and can immediately open the running application in their browser.

**Why this priority**: Onboarding friction is the stated core problem. If contributors cannot get the project running quickly, every other workflow improvement is moot. This is the MVP that delivers immediate, demonstrable value on its own.

**Independent Test**: Can be fully validated by cloning the repository into a fresh environment, running the install target then the dev target, and confirming the application is reachable in a browser — without consulting any command outside the documented target set.

**Acceptance Scenarios**:

1. **Given** a clean clone of the repository with the required runtimes installed but no dependencies, **When** the contributor runs the install target, **Then** all backend and frontend dependencies are installed and the project is ready to start.
2. **Given** dependencies are installed, **When** the contributor runs the dev target, **Then** the backend application and the frontend development server both start and the contributor can open the application in a browser.
3. **Given** the contributor does not know which commands are available, **When** they invoke the help target, **Then** they receive a clear, human-readable list of every available command with a one-line description of each.

---

### User Story 2 - Run the Full Test Suite With One Command (Priority: P1)

A developer has finished a change and wants to verify it before requesting review. They need to run the entire automated test suite — backend and frontend — including the project's mandatory coverage gate, using a single command instead of remembering two different test runners, coverage flags, and the threshold the project enforces.

**Why this priority**: The project's constitution treats the 85% coverage gate as non-negotiable, so making it trivial to run the complete suite is essential to preventing regressions and merge-blockers. Independently valuable: it improves developer confidence on every change.

**Independent Test**: Can be validated by making a deliberate change that lowers coverage and confirming the test target surfaces the failure clearly, then reverting and confirming success — using only the documented target.

**Acceptance Scenarios**:

1. **Given** the working copy has changes that pass all tests and meet coverage, **When** the developer runs the test target, **Then** the backend and frontend test suites both execute and the command reports overall success.
2. **Given** the working copy would drop coverage below the mandated threshold or break a test, **When** the developer runs the test target, **Then** the command fails with an actionable summary identifying which suite and which check did not pass.
3. **Given** a developer only wants feedback on one stack during active iteration, **When** they invoke a backend-only or frontend-only test variant, **Then** only that stack's tests run, while the aggregate test target always covers both.

---

### User Story 3 - Lint and Format Before Committing (Priority: P2)

Before pushing a branch for review, a developer wants to confirm the code meets the project's style and type-safety standards across both Python and TypeScript. They run one command that checks formatting, linting, and types so they can fix issues before the CI pipeline or a reviewer flags them.

**Why this priority**: Quality gates catch issues before review, reducing review cycles and keeping the codebase consistent. Important but secondary to getting running and testing, because a developer can still work without it.

**Independent Test**: Can be validated by introducing a style or type violation and confirming the lint target reports it, then fixing it and confirming success — using only the documented target.

**Acceptance Scenarios**:

1. **Given** the working copy contains a style, lint, or type error, **When** the developer runs the lint target, **Then** the command fails and reports the offending files and rule violations.
2. **Given** the working copy is clean across all checks, **When** the developer runs the lint target, **Then** the command succeeds without modification to the files.
3. **Given** a developer wants issues fixed automatically where possible, **When** they invoke an auto-fix variant, **Then** formatting and auto-fixable lint issues are corrected in place before the developer reviews the diff.

---

### User Story 4 - Build the Project for Production (Priority: P2)

A maintainer preparing a release needs to produce a deployable build of the application — compiled frontend assets and a production-ready container image consistent with how the project ships in production — without recalling the separate build and container steps.

**Why this priority**: A reliable production build path reduces release risk and parity bugs between local and deployed environments. Important for maintainers, but used less frequently than the daily dev/test/lint loop, hence P2.

**Independent Test**: Can be validated by running the build target and confirming the expected frontend artifacts are produced and a production container image is built, then smoke-testing that image serves the application.

**Acceptance Scenarios**:

1. **Given** all tests and checks pass, **When** the maintainer runs the build target, **Then** production frontend assets are compiled and the production container image is built.
2. **Given** the build target has run, **When** the resulting container image is started, **Then** the application starts and serves the built assets identically to the documented production deployment.
3. **Given** a maintainer only needs one artifact type, **When** they invoke a frontend-only or image-only build variant, **Then** only that artifact is produced, while the aggregate build target produces both.

---

### Edge Cases

- **Missing runtime**: A contributor runs a target on a machine without the required Python or Node version. The target should fail fast with a clear, human-readable message identifying the missing prerequisite rather than failing deep inside a dependency.
- **Dependencies not yet installed**: A contributor runs the dev, test, lint, or build target before installing dependencies. The target should detect the missing state and instruct the contributor to run the install target first (or report a clear failure) rather than producing cryptic module-not-found errors.
- **Port already in use**: The dev target is run when the application's port is occupied. It should surface the conflict clearly so the contributor understands how to resolve it (e.g., stop the conflicting process or use an alternate port).
- **Non-POSIX environment**: A contributor on a system without a POSIX-compatible `make` (for example, native Windows without a Unix-like shell) attempts to use the targets. The documentation should state the supported environments and recommended workaround (for example, a Unix-like shell) so the limitation is known up front.
- **Interrupted long-running target**: A contributor interrupts the dev or test target mid-run. Interrupting should cleanly terminate all spawned processes so no orphaned server or watcher keeps running in the background.
- **Coverage threshold edge**: The test suite passes but coverage lands exactly at or just below the gate. The test target must treat the mandated coverage floor as a hard failure so under-covered branches never pass locally.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST provide a single install command that installs all backend and all frontend dependencies in the correct order.
- **FR-002**: The project MUST provide a single dev command that starts both the backend application and the frontend live-reload server so the full development environment is reachable from one invocation.
- **FR-003**: The project MUST provide a single test command that runs the complete backend and frontend automated test suites, including coverage measurement for each stack.
- **FR-004**: The test command MUST enforce the project's mandated coverage floor as a hard pass/fail gate so a result below the threshold always fails the command.
- **FR-005**: The project MUST provide a single lint command that runs formatting, linting, and type-safety checks across both the backend and the frontend.
- **FR-006**: The project MUST provide a single build command that produces production-compiled frontend assets and a production-ready container image consistent with the project's documented production deployment.
- **FR-007**: The project MUST provide a help command that lists every available command with a concise human-readable description, and MUST serve as the default action when no command is specified.
- **FR-008**: The commands MUST reuse the project's already-approved canonical commands (the official server start script, the approved test runner invocation, the existing frontend scripts, and the container compose tooling) rather than introducing divergent or duplicate workflows.
- **FR-009**: The commands MUST include granular variants that target a single stack (backend-only and frontend-only) for install, test, lint, and build, in addition to the aggregate commands.
- **FR-010**: The dev and build commands MUST terminate all spawned processes cleanly when interrupted, leaving no orphaned background servers or watchers.
- **FR-011**: The new workflow files MUST be additive only and MUST NOT alter, remove, or break any existing documented command, script, or documented deployment path.
- **FR-012**: The commands MUST be documented, including the supported environments, prerequisites, and how to handle common failure modes (missing runtime, missing dependencies, port conflicts).

### Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new contributor can go from a clean clone to a running application in under 5 minutes using only the documented command set.
- **SC-002**: The number of distinct manual commands a developer must recall to perform the core daily tasks (install, dev, test, lint, build) is reduced to exactly one command per task.
- **SC-003**: 100% of the five core tasks — install, dev, test, lint, build — are executable with a single command that covers both the backend and the frontend.
- **SC-004**: Every execution of the test command surfaces the project's coverage gate, and any result below the mandated floor fails the command before a review is requested.
- **SC-005**: A production build produced by the build command behaves identically to the project's documented production deployment when the resulting artifacts are run.
- **SC-006**: A developer can discover all available commands and their purpose by running the help command, with no need to open the implementation files.

## Assumptions

- Contributors work on POSIX-compatible systems (macOS or Linux) where the `make` tool is available; contributors on other operating systems use a Unix-like shell environment, and this requirement is documented rather than silently assumed.
- The existing approved commands remain the single source of truth for each operation (the official server start script for running the app, the approved `python3 -m pytest` invocation for backend tests, the existing `npm` scripts for frontend tasks, and the container compose tooling for production). The new workflow wraps these commands; it does not replace them.
- The development environment consists of two concurrently running services — the backend application and the frontend development server — both of which a contributor needs running during normal development, so the dev target starts both.
- Backend dependencies and frontend dependencies are managed by their respective standard tooling already present in the repository, and the install target invokes each in the correct order.
- The production build consists of compiled frontend assets plus a production container image, mirroring the documented container-based deployment; granular single-artifact variants are provided for maintainers who need only one.
- The coverage floor enforced by the test command matches the figure already mandated by the project's constitution and test configuration.
- The feature is additive: it introduces the workflow file(s) and supporting documentation only and does not modify existing source code, scripts, or deployment definitions.
