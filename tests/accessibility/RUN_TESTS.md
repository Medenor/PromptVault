# Running Accessibility Tests

Complete guide for running and debugging PromptVault accessibility tests.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Running Tests](#running-tests)
- [Debugging](#debugging)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Ensure you have:

- **Node.js** 16+ (check with `node --version`)
- **npm** 7+ (check with `npm --version`)
- **Python** 3.8+ for running the application server
- **Playwright** browsers installed (automatically installed with `npm install`)

### Install Dependencies

```bash
# Install all project dependencies
npm install

# Playwright browsers should be installed automatically
# If not, install them explicitly:
npx playwright install
```

## Quick Start

### Run All Tests

```bash
# Run accessibility tests on chromium browser
npm run test:ui:accessibility

# Run on all browsers (chromium, firefox, webkit, mobile)
npm run test:ui:accessibility:all

# Run in headed mode (see browser window)
HEADED=1 npm run test:ui:accessibility
```

### Route Scans (axe-core) Without Maintaining Specs

If you want broad page coverage without relying on the `tests/accessibility/*.spec.ts` suite, use the Python runner:

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

### View Test Reports

```bash
# Open HTML report (after tests complete)
open playwright-report/index.html

# Or with custom report generator
npm run test:ui:accessibility:report
```

## Running Tests

### By Browser

#### Single Browser

```bash
# Chromium (default, fastest)
npx playwright test --project=chromium

# Firefox
npx playwright test --project=firefox

# WebKit (Safari)
npx playwright test --project=webkit

# Mobile Chrome
npx playwright test --project="Mobile Chrome"

# Mobile Safari
npx playwright test --project="Mobile Safari"
```

#### Multiple Browsers

```bash
# All browsers
npx playwright test

# Desktop browsers only
npx playwright test --project=chromium --project=firefox --project=webkit

# Mobile browsers only
npx playwright test --project="Mobile Chrome" --project="Mobile Safari"
```

### By Test File

```bash
# Run specific test file
npx playwright test main-page.spec.ts

# Run multiple files
npx playwright test main-page.spec.ts authentication.spec.ts

# Run tests matching pattern
npx playwright test --grep "main page"

# Run tests NOT matching pattern
npx playwright test --grep-invert "keyboard"
```

### By Test Suite

```bash
# Run specific describe block
npx playwright test --grep "^Main Page Accessibility"

# Run specific test with exact match
npx playwright test --grep "^Main Page.*Skip Link"
```

### Headless vs Headed Mode

```bash
# Headless (default, no browser window)
npm run test:ui:accessibility

# Headed (see browser window)
HEADED=1 npm run test:ui:accessibility

# UI mode (interactive debugging)
npx playwright test --ui

# UI mode for specific file
npx playwright test main-page.spec.ts --ui
```

## Debugging

### Debug Mode

```bash
# Stop on first test, inspect with Playwright Inspector
DEBUG=1 npx playwright test

# Debug specific test
DEBUG=1 npx playwright test --grep "specific test"
```

### View What Was Tested

```bash
# After tests complete, open report
open playwright-report/index.html

# Or view trace files for failed tests
open test-results/trace.zip
```

### Slow Motion

```bash
# Run tests with 1 second delay between actions (helps see what's happening)
npx playwright test --headed --slow-mo=1000
```

### Interactive Debugging with Playwright Inspector

```bash
# Use interactive step-through debugger
npx playwright test --debug

# Or in UI mode
npx playwright test --ui
```

### Check Test Setup

```bash
# Verify Playwright is installed correctly
npx playwright install

# Check which browsers are available
npx playwright install --with-deps
```

### Common Debug Techniques

#### Test a Single Test

```bash
# Run one test in debug mode
DEBUG=1 npx playwright test main-page.spec.ts --grep "Skip Link"
```

#### See Console Output

```bash
# Print all console logs from page
npx playwright test main-page.spec.ts --headed
# Browser console will show in terminal
```

#### Capture Screenshots

Tests automatically capture screenshots on failure. View in:
```
test-results/
├── main-page-spec-skip-link-[browser].png
└── ... other failures
```

#### Use page.pause()

Add to test code to pause execution:
```javascript
test('example', async ({ page }) => {
  await page.goto('/');
  await page.pause(); // Pauses here, use inspector to continue
});
```

## CI/CD Integration

### Forgejo Actions Example

```yaml
name: Accessibility Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - run: npm ci
      - run: npx playwright install --with-deps

      - run: npm run test:ui:accessibility

      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

### GitLab CI Example

```yaml
test:accessibility:
  image: mcr.microsoft.com/playwright:v1.40.1-jammy
  script:
    - npm ci
    - npm run test:ui:accessibility
  artifacts:
    when: always
    paths:
      - playwright-report/
    reports:
      junit: test-results/junit.xml
```

### Running in CI

```bash
# Set CI environment variable to optimize for CI
CI=1 npm run test:ui:accessibility

# This:
# - Runs tests serially (not in parallel)
# - Uses 1 worker instead of multiple
# - Disables retry on CI (set in config)
# - Generates reports
```

## Environment Variables

### Application Server

```bash
# Custom application URL (default: http://127.0.0.1:8003)
ACCESSIBILITY_BASE_URL=http://localhost:3000 npm run test:ui:accessibility

# Use external server (don't start dev server)
ACCESSIBILITY_EXTERNAL_SERVER=1 npm run test:ui:accessibility

# Start specific server port
ACCESSIBILITY_BASE_URL=http://127.0.0.1:8004 npm run test:ui:accessibility
```

### Authentication

```bash
# Set test user credentials
ACCESSIBILITY_USER_USERNAME=user@example.com \
ACCESSIBILITY_USER_PASSWORD=password123 \
npm run test:ui:accessibility

# Set admin credentials
ACCESSIBILITY_ADMIN_USERNAME=admin@example.com \
ACCESSIBILITY_ADMIN_PASSWORD=adminpass123 \
npm run test:ui:accessibility

# Use saved auth state (faster, avoids re-login)
ACCESSIBILITY_AUTH_STATE_DIR=/tmp/pw-auth npm run test:ui:accessibility

# Force fresh login each time
ACCESSIBILITY_FORCE_RELOGIN=1 npm run test:ui:accessibility
```

### Test Filtering

```bash
# Only test specific pages (comma-separated)
ACCESSIBILITY_PAGES=/,/auth/login,/auth/register npm run test:ui:accessibility

# Skip certain tests
ACCESSIBILITY_SKIP_KEYBOARD=1 npm run test:ui:accessibility
ACCESSIBILITY_SKIP_CONTRAST=1 npm run test:ui:accessibility
```

### Debugging Environment

```bash
# Show verbose output
npm run test:ui:accessibility -- --verbose

# Run in headed mode
HEADED=1 npm run test:ui:accessibility

# Run in debug mode
DEBUG=1 npx playwright test

# Use inspector
npx playwright test --debug
```

## Test Results Interpretation

### Console Output

```
✓ main-page.spec.ts (60 tests)
  ✓ Main Page Accessibility Tests (60 tests)
    ✓ Skip Link Functionality Tests (3 tests)
      ✓ should have visible skip link
      ✓ should navigate to main content with skip link
      ✓ should be keyboard accessible

Total: 60 passed in 45.2s
```

Success! All tests passed.

### Failed Tests

```
✗ main-page.spec.ts (1 failed, 59 passed)
  ✗ Main Page Accessibility Tests > Header Navigation Tests > should have proper tab order
    Error: Assertion failed
    at test.ts:123
```

Check:
1. Screenshot in `test-results/` directory
2. HTML report: `playwright-report/index.html`
3. Trace file for detailed debugging

### Report Files Generated

After test run, check:

```
playwright-report/       # HTML report
├── index.html          # Main report (open in browser)
└── ...

test-results/           # Detailed results
├── results.json        # JSON format
├── junit.xml           # JUnit format (for CI)
├── *.png               # Screenshots of failures
└── trace.zip           # Debugging traces
```

## Performance Tips

### Faster Test Runs

```bash
# Run in parallel (default)
npm run test:ui:accessibility

# Single browser is faster
npx playwright test --project=chromium

# Skip video/trace for faster runs
npx playwright test --no-trace --no-video
```

### Optimize Timeout

Tests have 60-second timeout by default. Adjust if needed:

```javascript
// In test file
test.setTimeout(120000); // 2 minutes for slow test
```

### Cache Auth State

Saves time by not re-authenticating:

```bash
# First run: authenticate and save
ACCESSIBILITY_AUTH_STATE_DIR=/tmp/pw-auth npm run test:ui:accessibility

# Subsequent runs: reuse auth
ACCESSIBILITY_AUTH_STATE_DIR=/tmp/pw-auth npm run test:ui:accessibility
```

## Troubleshooting

### Tests Won't Start

**Problem**: "Cannot find module" or "Port already in use"

```bash
# Kill process on port 8003
lsof -ti:8003 | xargs kill -9

# Or use different port
ACCESSIBILITY_BASE_URL=http://127.0.0.1:8004 npm run test:ui:accessibility
```

### Authentication Fails

**Problem**: "Login failed" or "Invalid credentials"

```bash
# Check credentials are correct
ACCESSIBILITY_USER_USERNAME=user@example.com \
ACCESSIBILITY_USER_PASSWORD=yourpassword \
npm run test:ui:accessibility

# Force fresh login
ACCESSIBILITY_FORCE_RELOGIN=1 npm run test:ui:accessibility

# Verify server is running
curl http://127.0.0.1:8003/api/auth/login
```

### Element Not Found

**Problem**: "locator.click() timed out" or "Element not found"

```bash
# Run in headed mode to see what's happening
HEADED=1 npx playwright test --grep "specific test"

# Run with debug to pause
DEBUG=1 npx playwright test --grep "specific test"
```

### Focus Indicator Not Visible

**Problem**: "Focus indicator not found"

Solution:
1. Verify CSS `:focus { outline: ... }` is set
2. Check element is actually focusable (tabindex, button, input, etc.)
3. Take screenshot to inspect visually

### Slow Tests

**Problem**: Tests taking too long

```bash
# Check timeout settings
grep "setTimeout" playwright.config.ts

# Run with timing info
npx playwright test --reporter=list

# Profile with trace
npx playwright test --trace=on
```

### Cross-Browser Issues

**Problem**: Test passes in Chrome but fails in Firefox

Solution:
1. Run both browsers separately to identify differences
2. Check browser-specific CSS or JavaScript
3. File browser-specific issues

## Advanced Usage

### Run Only New/Changed Tests

```bash
# Tests that are likely affected by changes
# (requires test naming convention)
npx playwright test --grep "my-feature"
```

### Generate Coverage Report

```bash
# Create detailed coverage report
npm run test:ui:accessibility:report

# View generated report
open accessibility-report.html
```

### Run Tests with Custom Reporter

```bash
# JSON output for parsing
npx playwright test --reporter=json > results.json

# Custom JUnit report
npx playwright test --reporter=junit
```

### Update Test Baselines

```bash
# If you intentionally changed visual appearance
# Update baseline screenshots:
npx playwright test --update-snapshots
```

## Getting Help

For additional help:

- **Playwright Docs**: https://playwright.dev
- **WCAG 2.1 Guidelines**: https://www.w3.org/WAI/WCAG21/quickref/
- **Playwright Inspector**: `npx playwright test --debug`
- **Check QUICK_START.md** for common functions
- **Check README.md** for full utility documentation
