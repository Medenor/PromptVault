# Accessibility Testing

This is the entry point for PromptVault accessibility testing. It deliberately stays high-level and points to the canonical docs, so we don’t maintain the same instructions in three places.

## Where To Start

- 5-minute “just run it”: `tests/accessibility/QUICK_START.md`
- Full “how to run/debug”: `tests/accessibility/RUN_TESTS.md`
- How the suite is organized / utilities: `tests/accessibility/README.md`
- Adding or extending tests: `tests/accessibility/CONTRIBUTING.md`

## What We Run

There are two complementary approaches:

1. **Spec-style accessibility tests** in `tests/accessibility/*.spec.ts` (structure, labels, keyboard, contrast, etc.). These are run via Playwright using `playwright.config.ts`.
2. **Route scanning** via `axe-core` (broad coverage) using `scripts/accessibility_test.py` and/or `scripts/playwright_accessibility_tests.ts`.

Use `RUN_TESTS.md` for the exact commands for both.

## Failure Policy (axe)

- We treat `critical` and `serious` axe violations as failures.
- Protected routes (`/auth/profile`, `/manage-*`, `/admin/*`) require credentials/session state to be scanned.
- We scan tags: `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`.

## Reports

- Default Playwright HTML report: `playwright-report/`
- Custom accessibility HTML report (if enabled): `accessibility-report/` (ignored by git)
