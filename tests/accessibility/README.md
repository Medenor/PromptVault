# Accessibility Testing Infrastructure

Comprehensive test infrastructure for automated WCAG 2.1 AA accessibility testing of PromptVault.

## Quick Links

Start here based on your task:

- **Overview?** → See [ACCESSIBILITY_TESTING.md](./ACCESSIBILITY_TESTING.md)
- **Running Tests?** → See [RUN_TESTS.md](./RUN_TESTS.md)
- **Writing Tests?** → See [CONTRIBUTING.md](./CONTRIBUTING.md)
- **Test Coverage?** → See [COVERAGE.md](./COVERAGE.md)
- **Quick Reference?** → See [QUICK_START.md](./QUICK_START.md)
- **Compliance Status?** → See [CHECKLIST.md](./CHECKLIST.md)

## Directory Structure

```
tests/accessibility/
├── utils/                           # Utility functions for accessibility testing
│   ├── contrast.js                 # Color contrast ratio calculations
│   ├── aria.js                     # ARIA attribute validation
│   ├── keyboard.js                 # Keyboard navigation testing
│   ├── screenshots.js              # Screenshot utilities for visual testing
│   └── index.js                    # Central export for all utilities
├── fixtures/                        # Test fixtures and helpers
│   ├── auth.js                     # Authentication fixtures and helpers
│   ├── test-data.ts                # Test data setup and management
│   └── index.js                    # Central export for fixtures
├── reporters/                       # Custom test reporters
│   └── html-reporter.ts            # Beautiful HTML test report generator
├── scripts/                         # Build and utility scripts
│   └── generate-summary.ts         # Generate test statistics and summary
├── reports/                         # Test report templates and output
│   └── report-template.json        # JSON schema for test reports
├── .forgejo-actions-example.yml     # Forgejo Actions CI/CD workflow example
├── visual-regression.config.ts     # Visual regression testing configuration
├── *.spec.ts                       # Test files (main-page, authentication, etc.)
├── README.md                       # This file
├── RUN_TESTS.md                    # Comprehensive testing guide
├── QUICK_START.md                  # Quick reference guide
├── CONTRIBUTING.md                 # Guide for adding new tests
├── COVERAGE.md                     # Detailed coverage breakdown
├── CHECKLIST.md                    # WCAG compliance checklist
└── SUMMARY.md                      # Auto-generated test summary
```

## Test Statistics

- **Canonical Test Files**: 8 maintained specs
- **Test Cases**: Use `npx playwright test tests/accessibility --list` for current count
- **Suite Strategy**: Domain-first canonical suite + focused smoke checks
- **WCAG Criteria Covered**: 25+ criteria from WCAG 2.1 AA
- **Coverage Rate**: See `COVERAGE.md` for current mapping and known gaps
- **Last Updated**: Auto-generated on each test run

## Canonical Spec Set

The accessibility suite is intentionally consolidated to these maintained files:

- `authentication.spec.ts`
- `main-page.spec.ts`
- `admin-pages.spec.ts`
- `category-management.spec.ts`
- `tag-management.spec.ts`
- `import-export.spec.ts`
- `backup-management.spec.ts`
- `focus-indicators.spec.ts`

This keeps CI signal high and avoids duplicate/debug variants.

## Test Tags

The canonical suite uses test-title tags for filtering:

- `@regression-a11y`: full canonical regression coverage
- `@smoke-a11y`: fast cross-page smoke checks
- `@diagnostic-a11y`: optional diagnostics (excluded from default CI)

## Utilities

### Contrast Testing (`utils/contrast.js`)

Validate color contrast ratios according to WCAG 2.1 standards.

#### Key Functions

- **`parseColor(color)`** - Parse CSS color strings to RGB values
  ```javascript
  const rgb = parseColor('rgb(255, 0, 0)');
  const rgb2 = parseColor('#FF0000');
  const rgb3 = parseColor('red');
  ```

- **`calculateRelativeLuminance(rgb)`** - Calculate relative luminance per WCAG 2.1
  ```javascript
  const lum = calculateRelativeLuminance({ r: 255, g: 255, b: 255 });
  ```

- **`calculateContrastRatio(color1, color2)`** - Calculate contrast ratio between colors
  ```javascript
  const ratio = calculateContrastRatio(
    { r: 0, g: 0, b: 0 },
    { r: 255, g: 255, b: 255 }
  ); // 21:1
  ```

- **`isContrastCompliant(ratio, level, type)`** - Check if ratio meets WCAG standards
  ```javascript
  // For WCAG AA text: requires 4.5:1
  isContrastCompliant(4.5, 'AA', 'text'); // true

  // For WCAG AA UI components: requires 3:1
  isContrastCompliant(3, 'AA', 'ui'); // true
  ```

- **`testTextContrast(page, element, wcagLevel)`** - Test text contrast on page
  ```javascript
  const result = await testTextContrast(page, page.locator('p'), 'AA');
  // Returns: { ratio, passes, foreground, background, required, violation }
  ```

- **`testUIContrast(page, element, wcagLevel)`** - Test UI component contrast
  ```javascript
  const result = await testUIContrast(page, page.locator('button'), 'AA');
  ```

- **`testContrastBatch(page, selector, wcagLevel, type)`** - Test multiple elements
  ```javascript
  const results = await testContrastBatch(page, 'button', 'AA', 'ui');
  ```

#### WCAG Contrast Standards

| Type | AA | AAA |
|------|----|----|
| Text | 4.5:1 | 7:1 |
| UI Components | 3:1 | 4.5:1 |

### ARIA Testing (`utils/aria.js`)

Validate ARIA attributes and semantic HTML structure.

#### Key Functions

- **`checkAccessibleName(element)`** - Check if element has accessible name
  ```javascript
  const nameInfo = await checkAccessibleName(page.locator('button'));
  // Returns: { hasAccessibleName, name, sources }
  ```

- **`validateAriaAttributes(element, requiredAttrs)`** - Validate ARIA attributes present
  ```javascript
  const result = await validateAriaAttributes(
    page.locator('[role="tablist"]'),
    ['role', 'aria-label']
  );
  // Returns: { valid, missing, present }
  ```

- **`checkLandmarkRegions(page)`** - Check for WCAG landmark regions
  ```javascript
  const landmarks = await checkLandmarkRegions(page);
  // Returns: { hasLandmarks, landmarks: [{role, count}] }
  ```

- **`validateFormLabels(page)`** - Verify all form inputs have labels
  ```javascript
  const labels = await validateFormLabels(page);
  // Returns: { allLabeled, labeled, unlabeled, unlabeledElements }
  ```

- **`validateButtonLabels(page)`** - Check all buttons have accessible names
  ```javascript
  const buttons = await validateButtonLabels(page);
  // Returns: { allButtonsLabeled, labeled, unlabeled, unlabeledSelectors }
  ```

- **`validateHeadingHierarchy(page)`** - Check heading level hierarchy
  ```javascript
  const hierarchy = await validateHeadingHierarchy(page);
  // Returns: { validHierarchy, headings, issues }
  ```

- **`checkLiveRegions(page)`** - Find ARIA live regions
  ```javascript
  const liveRegions = await checkLiveRegions(page);
  // Returns: { hasLiveRegions, regions: [{role, ariaLive, ariaAtomic}] }
  ```

### Keyboard Testing (`utils/keyboard.js`)

Test keyboard navigation and keyboard accessibility.

#### Key Functions

- **`extractTabOrder(page)`** - Get focusable elements in tab order
  ```javascript
  const tabOrder = await extractTabOrder(page);
  // Returns: [{selector, text, tabIndex, isNaturallyFocusable}]
  ```

- **`testKeyboardNavigation(page)`** - Test Tab key navigation
  ```javascript
  const result = await testKeyboardNavigation(page);
  // Returns: { success, tabOrder, focusableElements, issues }
  ```

- **`verifyFocusIndicators(page)`** - Check all focusable elements have visible focus
  ```javascript
  const result = await verifyFocusIndicators(page);
  // Returns: { hasFocusIndicators, elementsWithFocus, elementsWithoutFocus, details }
  ```

- **`testKeyboardShortcuts(page, shortcuts)`** - Test custom keyboard shortcuts
  ```javascript
  const results = await testKeyboardShortcuts(page, [
    { key: 'Control+S', expected: () => someCheckFunction() }
  ]);
  ```

- **`testBackwardNavigation(page)`** - Test Shift+Tab backward navigation
  ```javascript
  const result = await testBackwardNavigation(page);
  // Returns: { success, backwardTabOrder, issues }
  ```

- **`validateRovingTabindex(page, containerSelector)`** - Check roving tabindex pattern
  ```javascript
  const result = await validateRovingTabindex(page, '[role="tablist"]');
  // Returns: { isRovingTabindex, activeIndex, items, violations }
  ```

- **`validateSkipLinks(page)`** - Check for skip links
  ```javascript
  const skipLinks = await validateSkipLinks(page);
  // Returns: { hasSkipLink, skipLinks, issues }
  ```

### Screenshot Testing (`utils/screenshots.js`)

Capture and compare element screenshots in different states.

#### Key Functions

- **`captureNormalState(page, element, filename)`** - Capture element in normal state
- **`captureHoverState(page, element, filename)`** - Capture element on hover
- **`captureFocusState(page, element, filename)`** - Capture element when focused
- **`captureActiveState(page, element, filename)`** - Capture element when active/pressed
- **`captureErrorState(page, element, filename)`** - Capture element in error state
- **`captureDisabledState(page, element, filename)`** - Capture element when disabled

- **`captureElementStates(page, element, basePath)`** - Capture all states at once
  ```javascript
  const states = await captureElementStates(page, page.locator('button'), '/tmp/button');
  // Returns: { normal, hover, focus, active }
  ```

- **`capturePageWithHighlight(page, element, filename, color)`** - Capture page with highlighted element
  ```javascript
  await capturePageWithHighlight(page, page.locator('input'), '/tmp/highlight.png', 'red');
  ```

## Fixtures

### Authentication Fixtures (`fixtures/auth.js`)

Helpers for testing authenticated pages.

#### Key Exports

- **`login(page, username, password, attempt)`** - Login helper with retry logic
  ```javascript
  await login(page, 'user@example.com', 'password123');
  ```

- **`logout(page)`** - Logout current user
  ```javascript
  await logout(page);
  ```

- **`authenticatedUserTest`** - Fixture for user-level tests
  ```javascript
  import { authenticatedUserTest } from '@/fixtures/auth.js';

  authenticatedUserTest('should access user profile', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/auth/profile');
    // authenticated as regular user
  });
  ```

- **`authenticatedAdminTest`** - Fixture for admin-level tests
  ```javascript
  import { authenticatedAdminTest } from '@/fixtures/auth.js';

  authenticatedAdminTest('should access admin panel', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/admin/users');
    // authenticated as admin
  });
  ```

- **`dualAuthTest`** - Fixture for testing both user and admin paths
  ```javascript
  import { dualAuthTest } from '@/fixtures/auth.js';

  dualAuthTest('should have different access', async ({ authenticatedPages }) => {
    // authenticatedPages is array of [{role, page, context}]
    const userPage = authenticatedPages.find(p => p.role === 'user').page;
    const adminPage = authenticatedPages.find(p => p.role === 'admin').page;
  });
  ```

- **`getBaseURL()`** - Get configured base URL
- **`navigateToProtectedRoute(page, route)`** - Navigate to protected page
- **`isAuthenticated(page)`** - Check if user is authenticated
- **`clearAuthState(page)`** - Clear authentication cookies/storage

## Usage Examples

### Basic Accessibility Test

```javascript
import { test, expect } from '@playwright/test';
import { testTextContrast, validateFormLabels, checkLandmarkRegions } from '@/utils';

test('login page meets WCAG 2.1 AA standards', async ({ page }) => {
  await page.goto('/auth/login');

  // Test contrast on labels
  const labelContrast = await testTextContrast(page, page.locator('label'), 'AA');
  expect(labelContrast.passes).toBe(true);

  // Test form is properly labeled
  const labels = await validateFormLabels(page);
  expect(labels.allLabeled).toBe(true);

  // Test page has landmark regions
  const landmarks = await checkLandmarkRegions(page);
  expect(landmarks.hasLandmarks).toBe(true);
});
```

### Keyboard Navigation Test

```javascript
import { test, expect } from '@playwright/test';
import { testKeyboardNavigation, verifyFocusIndicators } from '@/utils';

test('dialog is keyboard accessible', async ({ page }) => {
  await page.goto('/');
  await page.locator('button:has-text("Open")').click();

  // Test Tab navigation works
  const navResult = await testKeyboardNavigation(page);
  expect(navResult.success).toBe(true);

  // Test all elements have visible focus
  const focusResult = await verifyFocusIndicators(page);
  expect(focusResult.elementsWithoutFocus).toBe(0);
});
```

### Authenticated Page Test

```javascript
import { authenticatedUserTest } from '@/fixtures/auth.js';
import { validateAriaAttributes } from '@/utils';

authenticatedUserTest('profile page is accessible', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/auth/profile');

  // Test form fields have proper ARIA labels
  const formLabels = await validateFormLabels(authenticatedPage);
  expect(formLabels.allLabeled).toBe(true);
});
```

## Environment Variables

Configure accessibility testing with environment variables:

```bash
# Base URL for tests (default: http://127.0.0.1:8003)
ACCESSIBILITY_BASE_URL=http://localhost:8003

# Regular user credentials for protected page testing
ACCESSIBILITY_USER_USERNAME=user@example.com
ACCESSIBILITY_USER_PASSWORD=password123

# Admin credentials for admin page testing
ACCESSIBILITY_ADMIN_USERNAME=admin@example.com
ACCESSIBILITY_ADMIN_PASSWORD=adminpass123

# Reuse auth state to avoid rate limiting
ACCESSIBILITY_AUTH_STATE_DIR=/tmp/pw-state

# Force re-login (don't reuse saved state)
ACCESSIBILITY_FORCE_RELOGIN=0

# Use external server (don't start server automatically)
ACCESSIBILITY_EXTERNAL_SERVER=1

# Run in headed mode for debugging
HEADED=1

# Pages to test (comma-separated, default: all pages)
ACCESSIBILITY_PAGES=/,/auth/login,/auth/register
```

## Running Tests

```bash
# Run accessibility tests in chromium
npm run test:ui:accessibility

# Run against all browsers
npm run test:ui:accessibility:all

# Run in headed mode for debugging
HEADED=1 npm run test:ui:accessibility

# Run with custom configuration
ACCESSIBILITY_BASE_URL=http://custom:3000 npm run test:ui:accessibility

# Run with UI mode
npx playwright test --project=chromium --ui
```

## Report Structure

Test results are saved to `tests/accessibility/reports/` as JSON files following the schema in `report-template.json`.

Key report sections:

- **metadata** - Test execution info (timestamp, environment, duration)
- **summary** - High-level pass/fail counts and violation totals
- **pages** - Detailed results per page (axe violations, contrast tests, keyboard tests)
- **issues** - Aggregated issues organized by impact level
- **recommendations** - Suggested fixes for failing issues

## Best Practices

### Writing Tests

1. **Test complete user journeys** - Don't just test individual pages
2. **Use semantic HTML** - Reduces need for ARIA attributes
3. **Test with real users** - Automated testing can't catch everything
4. **Include both public and authenticated pages**
5. **Test responsive/mobile viewports**

### Maintenance

1. **Keep utilities focused** - One responsibility per utility file
2. **Document with JSDoc** - Include parameter types and examples
3. **Handle errors gracefully** - Don't let individual element failures crash tests
4. **Cache results** - Store auth state to avoid rate limiting
5. **Update as standards evolve** - WCAG guidelines change

## Related Documentation

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Playwright Documentation](https://playwright.dev)
- [axe-core Rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)

## Documentation Files

### For Test Runners
- **[RUN_TESTS.md](./RUN_TESTS.md)** - Complete guide for running, debugging, and CI/CD integration
  - Commands for different browsers and test files
  - Debugging techniques and tools
  - Forgejo Actions and GitLab CI examples
  - Troubleshooting common issues

### For Test Writers
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Guide for writing new accessibility tests
  - Test file structure and naming conventions
  - Best practices and patterns
  - Using utility functions
  - Example tests and common patterns
  - Submission checklist

### For Coverage Analysis
- **[COVERAGE.md](./COVERAGE.md)** - Detailed breakdown of what's tested
  - WCAG 2.1 AA criteria mapping
  - Page-by-page coverage
  - Component coverage
  - Known limitations and gaps
  - Future improvements

### For Quick Reference
- **[QUICK_START.md](./QUICK_START.md)** - Fast reference guide
  - Common utility functions
  - Environment variables
  - Troubleshooting tips
  - WCAG quick reference

### For Compliance Tracking
- **[CHECKLIST.md](./CHECKLIST.md)** - Interactive WCAG 2.1 AA checklist
  - All 50 criteria with status
  - Test coverage percentage
  - Manual testing items
  - Status tracking

### For Configuration
- **[.forgejo-actions-example.yml](./.forgejo-actions-example.yml)** - CI/CD workflow template
  - Forgejo Actions examples
  - GitLab CI examples
  - PR commenting
  - Scheduled reports

- **[visual-regression.config.ts](./visual-regression.config.ts)** - Visual regression settings
  - Focus indicator testing
  - State-based visual comparisons
  - Browser-specific considerations

### For Data Management
- **[fixtures/test-data.ts](./fixtures/test-data.ts)** - Test data management
  - Create test prompts, categories, tags
  - Cleanup test data
  - Seed database for testing
  - Export test metadata

### For Report Generation
- **[reporters/html-reporter.ts](./reporters/html-reporter.ts)** - Custom HTML reporter
  - Beautiful test report generation
  - WCAG criteria coverage display
  - Page-by-page results
  - Failed test details

- **[scripts/generate-summary.ts](./scripts/generate-summary.ts)** - Test summary generator
  - Analyze test files
  - Generate statistics
  - Create markdown summaries
  - Update README

## Getting Started

### 1. Run Tests (5 minutes)
```bash
npm run test:ui:accessibility
# View report: open playwright-report/index.html
```

### 2. Write a Test (15 minutes)
```bash
# See CONTRIBUTING.md for detailed guide
# Copy pattern from existing test file
# Run: npx playwright test --grep "your test"
```

### 3. Debug a Failure (10 minutes)
```bash
# Run in debug mode
HEADED=1 npx playwright test --grep "failing test"
# Use Playwright Inspector to step through
```

### 4. Generate Report (2 minutes)
```bash
npm run test:ui:accessibility:report
# View at: accessibility-report/index.html
```

## Test Execution Examples

### Run Everything
```bash
npm run test:ui:accessibility           # Chromium only
npm run test:ui:accessibility:all      # All browsers
```

### Run Specific Tests
```bash
npx playwright test main-page.spec.ts              # Single file
npx playwright test --grep "contrast"              # Test pattern
npx playwright test --project=firefox              # Specific browser
```

### Debug and Develop
```bash
HEADED=1 npm run test:ui:accessibility            # See browser
DEBUG=1 npx playwright test                        # Inspector mode
npx playwright test --ui                          # Interactive UI
```

### Generate Reports
```bash
npm run test:ui:accessibility:report               # HTML report
npm run test:ui:accessibility:summary              # Statistics
```

## CI/CD Integration

### Forgejo Actions
Copy [.forgejo-actions-example.yml](./.forgejo-actions-example.yml) to `.forgejo/workflows/accessibility-tests.yml`

Includes:
- Automatic test runs on push and PR
- Multi-browser testing
- HTML report artifacts
- PR comments with results
- Daily scheduled reports

### Local Verification
```bash
# Run tests before committing
npm run test:ui:accessibility

# Update coverage docs
npm run test:ui:accessibility:summary

# Commit if passing
git add tests/accessibility
git commit -m "test: update accessibility test results"
```

## Contributing

When adding new accessibility utilities:

1. Place in appropriate `utils/` file based on concern (contrast, aria, keyboard)
2. Add comprehensive JSDoc comments with examples
3. Export from `utils/index.js`
4. Add example usage to this README
5. Include error handling for edge cases
6. Test with actual Playwright pages when possible

## Submitting Test Improvements

1. Read [CONTRIBUTING.md](./CONTRIBUTING.md)
2. Create test file or update existing
3. Follow naming conventions and patterns
4. Run tests locally: `npm run test:ui:accessibility`
5. Update [COVERAGE.md](./COVERAGE.md) if adding new criteria
6. Submit PR with summary of changes
