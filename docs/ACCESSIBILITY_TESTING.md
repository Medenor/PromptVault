# Accessibility Testing Guide

This guide documents the first accessibility test tooling added for WCAG 2.1 AA work.

## Scope

- Automated scans with `axe-core` + Playwright
- Local runner script for repeatable audits
- Initial page coverage:
1. `/`
2. `/import-export`
3. `/backup-management`
4. `/auth/login`
5. `/auth/register`

## Prerequisites

- Node.js dependencies installed (`npm install`)
- Playwright browsers installed (`npm run playwright:install`)
- Application running on `http://127.0.0.1:8003`, or pass a custom URL

## Run Accessibility Scans

### NPM scripts

```bash
npm run test:ui:accessibility
```

```bash
npm run test:ui:accessibility:all
```

Lighthouse (accessibility score threshold enforced via `lighthouserc.json`):

```bash
npm run test:ui:lighthouse
```

### Python runner

```bash
python3 scripts/accessibility_test.py --verbose
```

Custom base URL:

```bash
python3 scripts/accessibility_test.py --base-url http://127.0.0.1:8001 --verbose
```

Specific pages only:

```bash
python3 scripts/accessibility_test.py --page /auth/login --page /auth/register --verbose
```

Protected pages with credentials:

```bash
ACCESSIBILITY_USER_USERNAME=test_user \
ACCESSIBILITY_USER_PASSWORD='your_password' \
ACCESSIBILITY_ADMIN_USERNAME=test_admin \
ACCESSIBILITY_ADMIN_PASSWORD='your_admin_password' \
python3 scripts/accessibility_test.py --page /auth/profile --page /admin/users --verbose
```

## Current Failure Policy

- Tests fail on `critical` and `serious` axe violations.
- Protected routes (`/auth/profile`, `/manage-*`, `/admin/*`) are scanned only when matching credentials are provided through env vars.
- Public routes returning non-HTML responses are skipped with a clear message.
- Rule tags scanned:
1. `wcag2a`
2. `wcag2aa`
3. `wcag21a`
4. `wcag21aa`

## Files Added/Updated

- `scripts/playwright_accessibility_tests.ts`
- `scripts/accessibility_test.py`
- `playwright.config.ts`
- `package.json`
