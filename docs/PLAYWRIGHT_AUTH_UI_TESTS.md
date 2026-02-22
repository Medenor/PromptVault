# AUTH-UI Playwright Tests

Comprehensive browser automation tests for PromptVault authentication UI using Playwright.

## Overview

These tests verify the user interface and user experience of the authentication system, including:

- Login and registration pages
- Form validation and error handling
- Password visibility toggle
- Login/logout flows
- Profile access
- Admin panel access
- Language switcher
- Responsive design (mobile/tablet/desktop)

## Prerequisites

- Python 3.14+
- Node.js 18+ (for Playwright)
- PromptVault server running on http://127.0.0.1:8003
- SQLAlchemy/PostgreSQL or SQLite database

## Installation

### 1. Install Playwright

```bash
# Install Playwright and browsers
npm install
npx playwright install
```

Or:

```bash
npm run playwright:install
```

### 2. Initialize Test Accounts

```bash
# Create test admin and regular user accounts
python3 scripts/init_test_admin.py
```

This creates:

- **Admin User**: `test_admin_ui` / `TestAdmin@Pass123456`
- **Regular User**: `test_user_ui` / `TestUser@Pass123456`

## Running Tests

### Quick Start

Run all AUTH-UI tests with UI (recommended for first run):

```bash
npm run test:ui
```

### Advanced Options

#### Run all tests with automatic server startup

```bash
bash scripts/run_playwright_tests.sh
```

#### Run tests in headed mode (see browser window)

```bash
npm run test:ui:headed
```

Or with environment variable:

```bash
HEADED=1 npx playwright test scripts/playwright_auth_ui_tests.ts
```

#### Run tests in debug mode (step through tests)

```bash
npm run test:ui:debug
```

#### Run specific test

```bash
npx playwright test scripts/playwright_auth_ui_tests.ts -g "AUTH-UI-005"
```

#### Run on specific browser

```bash
# Chrome only
npx playwright test scripts/playwright_auth_ui_tests.ts --project chromium

# Firefox only
npx playwright test scripts/playwright_auth_ui_tests.ts --project firefox

# Safari only
npx playwright test scripts/playwright_auth_ui_tests.ts --project webkit
```

#### Run on mobile viewports

```bash
# Mobile Chrome (Pixel 5)
npx playwright test scripts/playwright_auth_ui_tests.ts --project "Mobile Chrome"

# Mobile Safari (iPhone 12)
npx playwright test scripts/playwright_auth_ui_tests.ts --project "Mobile Safari"
```

## Test Cases

### AUTH-UI-001: Login Page Renders Correctly

- ✅ Page title matches
- ✅ Username field visible
- ✅ Password field visible
- ✅ Login button visible
- ✅ Register link visible
- ✅ Forgot password link visible

### AUTH-UI-002: Registration Page Renders Correctly

- ✅ Page title matches
- ✅ Username field visible
- ✅ Email field visible
- ✅ Password field visible
- ✅ Confirm password field visible
- ✅ Register button visible
- ✅ Login link visible
- ✅ Password strength indicator present

### AUTH-UI-003: Password Visibility Toggle

- ✅ Toggle button visible
- ✅ Click toggle shows password (type changes to text)
- ✅ Click again hides password (type changes to password)

### AUTH-UI-004: Form Validation - Empty Fields

- ✅ Clicking login without fields shows error
- ✅ Error message displayed
- ✅ User stays on login page

### AUTH-UI-005: Successful Login Flow

- ✅ User can login with valid credentials
- ✅ Redirects to home/dashboard
- ✅ Logout button or user menu visible

### AUTH-UI-006: Logout Flow

- ✅ Logout button/link found
- ✅ Click logout redirects to login
- ✅ Logout button no longer visible

### AUTH-UI-007: Profile Page Access

- ✅ Profile link visible when logged in
- ✅ Profile page loads
- ✅ Profile information displayed

### AUTH-UI-008: Admin Panel Access (Admin Only)

- ✅ Admin user sees admin link
- ✅ Admin panel page loads
- ✅ Admin interface visible

### AUTH-UI-009: Language Switcher

- ✅ Language switcher found
- ✅ Clicking changes language
- ✅ UI content changes

### AUTH-UI-010: Responsive Design - Mobile View

- ✅ Mobile viewport (375x667) tested
- ✅ Form fits within viewport
- ✅ Form elements are tappable (30px+ height)

## Test Reports

After running tests, reports are generated:

- **HTML Report**: `playwright-report/index.html`
- **JSON Results**: `test-results/results.json`
- **JUnit Report**: `test-results/junit.xml`
- **Screenshots**: `test-results/` (on failure)
- **Videos**: `test-results/` (on failure)

View HTML report:

```bash
npx playwright show-report
```

## Environment Variables

Configure test behavior with environment variables:

```bash
# Base URL of PromptVault server
BASE_URL=http://127.0.0.1:8003

# Test account credentials (auto-created by init_test_admin.py)
TEST_ADMIN_USERNAME=test_admin_ui
TEST_ADMIN_EMAIL=test_admin_ui@example.com
TEST_ADMIN_PASSWORD=TestAdmin@Pass123456

TEST_USER_USERNAME=test_user_ui
TEST_USER_EMAIL=test_user_ui@example.com
TEST_USER_PASSWORD=TestUser@Pass123456

# Run options
DEBUG=1              # Run in debug mode (step through)
HEADED=1             # Show browser window
CI=1                 # CI mode (retries, no parallelization)
```

Example:

```bash
BASE_URL=http://127.0.0.1:8003 HEADED=1 npm run test:ui
```

## Troubleshooting

### Tests fail with "Cannot find element"

1. Verify application is running: `curl http://127.0.0.1:8003`
2. Check element selectors match your HTML structure
3. Run in headed mode to see what's happening: `npm run test:ui:headed`

### "Browser not installed" error

Install Playwright browsers:

```bash
npx playwright install
```

### Test account creation fails

1. Ensure database is set up: `python3 -m pytest tests/ --cov`
2. Check database permissions
3. Verify application is running and database is accessible

### Tests timeout

1. Increase timeout in `playwright.config.ts`:

   ```typescript
   timeout: 60 * 1000; // 60 seconds
   ```

2. Run with more time:
   ```bash
   npx playwright test scripts/playwright_auth_ui_tests.ts --timeout=60000
   ```

### Server port in use

If port 8003 is already in use:

```bash
# Kill process using port 8003
lsof -ti:8003 | xargs kill -9

# Or use different port
PORT=8004 python3 run_web.py
BASE_URL=http://127.0.0.1:8004 npm run test:ui
```

## Best Practices

1. **Run before commits**: Use tests to verify UI changes don't break authentication
2. **Test on mobile**: Run mobile viewport tests: `npm run test:ui -- --project "Mobile Chrome"`
3. **Use debug mode**: When tests fail: `npm run test:ui:debug`
4. **Review reports**: Always check HTML report for failures: `npx playwright show-report`
5. **Keep selectors stable**: Use stable selectors (id, data-testid) instead of dynamic ones

## CI/CD Integration

### Forgejo Actions

```yaml
name: AUTH-UI Tests

on: [push, pull_request]

jobs:
  playwright:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - uses: actions/setup-python@v4
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: npm install && npx playwright install

      - name: Start server
        run: PORT=8003 python3 run_web.py &

      - name: Initialize test accounts
        run: python3 scripts/init_test_admin.py

      - name: Run Playwright tests
        run: npx playwright test scripts/playwright_auth_ui_tests.ts

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

## Contributing

To add new AUTH-UI tests:

1. Create test function in `scripts/playwright_auth_ui_tests.ts`
2. Follow naming convention: `test('AUTH-UI-XXX: Description', async ({ page }) => {})`
3. Use helper functions: `loginTestUser()`, `registerTestUser()`
4. Test both success and failure cases
5. Update this README with new test case
6. Run full test suite: `npm run test:ui`

## Related Documentation

- [Authentication API Guide](../AUTHENTICATION_API.md)
- [Authentication Deployment](../AUTHENTICATION_DEPLOYMENT.md)
- [Testing Guide](../TESTING.md)
- [Playwright Documentation](https://playwright.dev)
