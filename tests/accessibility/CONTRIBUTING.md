// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Contributing Accessibility Tests

Guide for adding new accessibility tests to PromptVault.

## Table of Contents

- [Getting Started](#getting-started)
- [Test File Structure](#test-file-structure)
- [Writing Tests](#writing-tests)
- [Naming Conventions](#naming-conventions)
- [Using Utility Functions](#using-utility-functions)
- [Best Practices](#best-practices)
- [Examples](#examples)
- [Common Patterns](#common-patterns)
- [Testing Tips](#testing-tips)
- [Submission Checklist](#submission-checklist)

## Getting Started

### Prerequisites

1. Understand WCAG 2.1 AA standards
2. Familiar with Playwright API
3. Review existing test files
4. Read main `README.md` for utility documentation

### Development Setup

```bash
# Clone and install
git clone <repo>
npm install

# Start development server
npm run dev

# Run tests in UI mode for debugging
npx playwright test --ui
```

## Test File Structure

### File Organization

Tests are organized by page/feature:

```
tests/accessibility/
├── main-page.spec.ts              # Home page tests
├── authentication.spec.ts         # Login/register pages
├── category-management.spec.ts   # Category CRUD
├── tag-management.spec.ts        # Tag CRUD
├── import-export.spec.ts         # Import/export feature
├── backup-management.spec.ts     # Backup feature
├── admin-pages.spec.ts           # Admin pages
└── [your-new-feature].spec.ts   # New feature tests
```

### Minimum File Structure

```typescript
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Accessibility tests for [Feature Name]
 * Tests cover WCAG 2.1 AA compliance including:
 * - [Criteria 1]
 * - [Criteria 2]
 * - [Criteria 3]
 */

import { test, expect } from '@playwright/test';
import {
  // Import utilities you'll use
  validateFormLabels,
  testTextContrast,
  testKeyboardNavigation,
} from './utils/index.js';
import { authenticatedUserTest } from './fixtures/auth.js';

test.describe('[Feature Name] Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Setup for each test
    await page.goto('/path/to/page', { waitUntil: 'networkidle' });
  });

  test.describe('[Test Group Name]', () => {
    test('should [expected behavior]', async ({ page }) => {
      // Test implementation
    });
  });
});
```

## Writing Tests

### Test Template

```typescript
test('[feature] should [expected behavior]', async ({ page }) => {
  // 1. SETUP - Navigate and prepare page state
  await page.goto('/path', { waitUntil: 'networkidle' });

  // 2. ACTION - Perform the action to test
  await page.locator('button').click();

  // 3. ASSERT - Check accessibility compliance
  expect(result).toBe(expectedValue);
});
```

### Test Anatomy

```typescript
test('form should be properly labeled', async ({ page }) => {
  // SETUP
  await page.goto('/auth/login');

  // ACTION - Get form labels
  const labelResults = await validateFormLabels(page);

  // ASSERT - Check all inputs have labels
  expect(labelResults.allLabeled).toBe(true);
  expect(labelResults.unlabeledElements).toHaveLength(0);
});
```

### Using Describe Blocks

Organize related tests:

```typescript
test.describe('Form Accessibility', () => {
  test('should have labels for all inputs', async ({ page }) => {
    // ...
  });

  test('should validate required fields', async ({ page }) => {
    // ...
  });
});
```

## Naming Conventions

### File Naming

```
[feature-name].spec.ts

Examples:
- main-page.spec.ts
- authentication.spec.ts
- user-profile.spec.ts
```

### Test Suite Naming

```typescript
test.describe('[Feature Name] Accessibility Tests', () => {
  // Tests grouped by feature
});

Examples: -'Main Page Accessibility Tests' -
  'Authentication Accessibility Tests' -
  'Form Accessibility Tests';
```

### Test Group Naming

```typescript
test.describe('[Specific Area] Tests', () => {
  // Related tests grouped together
});

Examples: -'Skip Link Functionality Tests' -
  'Keyboard Navigation Tests' -
  'Color Contrast Tests' -
  'Form Label Tests';
```

### Individual Test Naming

Use clear, descriptive names:

```typescript
test('should have visible skip link', async ({ page }) => {});
test('should navigate to main content with skip link', async ({ page }) => {});
test('should have 4.5:1 contrast ratio on labels', async ({ page }) => {});
```

**Bad naming** ❌

```typescript
test('test 1', async ({ page }) => {});
test('it works', async ({ page }) => {});
test('check labels', async ({ page }) => {});
```

## Using Utility Functions

### Available Utilities

#### Contrast Testing

```typescript
import { testTextContrast, testUIContrast, testContrastBatch } from './utils/index.js';

// Test single element
const result = await testTextContrast(page, page.locator('p'), 'AA');
expect(result.passes).toBe(true);

// Test multiple elements
const results = await testContrastBatch(page, 'button', 'AA', 'ui');
```

#### ARIA & Labeling

```typescript
import {
  validateFormLabels,
  validateButtonLabels,
  checkAccessibleName,
  validateAriaAttributes,
} from './utils/index.js';

// Check all inputs have labels
const labels = await validateFormLabels(page);
expect(labels.allLabeled).toBe(true);

// Check button has accessible name
const name = await checkAccessibleName(page.locator('button'));
expect(name.hasAccessibleName).toBe(true);
```

#### Structure & Semantics

```typescript
import {
  checkLandmarkRegions,
  validateHeadingHierarchy,
  validateAriaAttributes,
  checkLiveRegions,
} from './utils/index.js';

// Check page has landmarks
const landmarks = await checkLandmarkRegions(page);
expect(landmarks.hasLandmarks).toBe(true);

// Check heading hierarchy
const hierarchy = await validateHeadingHierarchy(page);
expect(hierarchy.validHierarchy).toBe(true);
```

#### Keyboard Navigation

```typescript
import {
  testKeyboardNavigation,
  verifyFocusIndicators,
  extractTabOrder,
  validateRovingTabindex,
  validateSkipLinks,
} from './utils/index.js';

// Test Tab navigation works
const nav = await testKeyboardNavigation(page);
expect(nav.success).toBe(true);

// Test focus is visible
const focus = await verifyFocusIndicators(page);
expect(focus.elementsWithoutFocus).toBe(0);

// Test skip links
const skipLinks = await validateSkipLinks(page);
expect(skipLinks.hasSkipLink).toBe(true);
```

#### Screenshots

```typescript
import {
  captureNormalState,
  captureFocusState,
  captureElementStates,
  capturePageWithHighlight,
} from './utils/index.js';

// Capture element in focus state
await captureFocusState(page, page.locator('button'), '/tmp/btn-focus.png');

// Capture all states
const states = await captureElementStates(page, page.locator('input'), '/tmp/input');
```

## Best Practices

### 1. Use Semantic Locators

```javascript
// Good - uses accessible properties
page.locator('button[aria-label="Close"]');
page.locator('input[aria-label="Search"]');

// Also good - uses visible text
page.locator('button:has-text("Submit")');

// Avoid - too specific or fragile
page.locator('.btn-close-xyz-123');
page.locator('div:nth-child(3) > button');
```

### 2. Wait for Network

```javascript
// Good - waits for network
await page.goto('/page', { waitUntil: 'networkidle' });

// Good - waits for specific element
await page.locator('main').waitFor({ state: 'visible' });

// Avoid - arbitrary delays
await page.waitForTimeout(1000); // Don't use!
```

### 3. Test Complete Workflows

```javascript
// Good - tests realistic user journey
test('user can search and filter results', async ({ page }) => {
  await page.goto('/');
  await page.locator('input[aria-label="Search"]').fill('query');
  await page.locator('button:has-text("Search")').click();
  const results = await page.locator('[role="article"]').count();
  expect(results).toBeGreaterThan(0);
});

// Avoid - testing single isolated actions
test('search input exists', async ({ page }) => {
  await page.goto('/');
  const input = page.locator('input[aria-label="Search"]');
  expect(input).toBeDefined();
});
```

### 4. Handle Dynamic Content

```javascript
// Good - waits for dynamic content
test('dynamic list is accessible', async ({ page }) => {
  await page.goto('/');
  await page.locator('button:has-text("Load More")').click();

  // Wait for new content
  await page.locator('[aria-live="polite"]').waitFor({ state: 'visible' });

  // Check accessibility of dynamic content
  const labels = await validateFormLabels(page);
  expect(labels.allLabeled).toBe(true);
});

// Avoid - assuming content is immediately available
test('list has labels', async ({ page }) => {
  await page.goto('/');
  const labels = await validateFormLabels(page);
  expect(labels.allLabeled).toBe(true);
});
```

### 5. Use Authentication Fixtures

```javascript
// For public pages
test('public page is accessible', async ({ page }) => {
  await page.goto('/public');
  // ...
});

// For authenticated pages
import { authenticatedUserTest } from './fixtures/auth.js';

authenticatedUserTest('profile page is accessible', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/profile');
  // ...
});

// For admin pages
import { authenticatedAdminTest } from './fixtures/auth.js';

authenticatedAdminTest('admin panel is accessible', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/admin');
  // ...
});
```

### 6. Focus on WCAG Criteria

```javascript
// Good - focuses on specific WCAG criterion
test('has 4.5:1 contrast (WCAG 1.4.3)', async ({ page }) => {
  const result = await testTextContrast(page, page.locator('p'), 'AA');
  expect(result.passes).toBe(true); // 4.5:1 minimum
});

// Good - multiple criteria in related test group
test.describe('Form Accessibility (WCAG 3.3.2, 2.1.1)', () => {
  test('labels present', async ({ page }) => {
    /* ... */
  });
  test('keyboard navigable', async ({ page }) => {
    /* ... */
  });
});

// Avoid - generic test names
test('form works', async ({ page }) => {
  // What specifically is being tested?
});
```

## Examples

### Example 1: Simple Form Test

```typescript
test('login form is accessible', async ({ page }) => {
  await page.goto('/auth/login', { waitUntil: 'networkidle' });

  // WCAG 3.3.2: All form inputs should have labels
  const labels = await validateFormLabels(page);
  expect(labels.allLabeled).toBe(true);

  // WCAG 2.1.1: All inputs should be keyboard accessible
  const nav = await testKeyboardNavigation(page);
  expect(nav.success).toBe(true);

  // WCAG 1.4.3: Text should have sufficient contrast
  const contrast = await testTextContrast(page, page.locator('label'), 'AA');
  expect(contrast.passes).toBe(true);

  // WCAG 2.4.7: Focus should be visible
  const focus = await verifyFocusIndicators(page);
  expect(focus.elementsWithoutFocus).toBe(0);
});
```

### Example 2: Dialog Accessibility

```typescript
test('modal dialog is accessible', async ({ page }) => {
  await page.goto('/');

  // Open dialog
  await page.locator('button:has-text("Open")').click();
  const dialog = page.locator('[role="dialog"]');
  await dialog.waitFor({ state: 'visible' });

  // WCAG 2.4.3: Focus should move into dialog
  await page.keyboard.press('Tab');
  const focused = page.locator('[role="dialog"] *:focus');
  await expect(focused).toBeInViewport();

  // WCAG 2.1.2: Escape should close dialog
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
});
```

### Example 3: Authenticated Page Test

```typescript
authenticatedUserTest('user profile page is accessible', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/profile', { waitUntil: 'networkidle' });

  // Test form accessibility
  const labels = await validateFormLabels(authenticatedPage);
  expect(labels.allLabeled).toBe(true);

  // Test keyboard navigation
  const nav = await testKeyboardNavigation(authenticatedPage);
  expect(nav.success).toBe(true);

  // Test contrast
  const contrast = await testTextContrast(
    authenticatedPage,
    authenticatedPage.locator('input'),
    'AA'
  );
  expect(contrast.passes).toBe(true);
});
```

## Common Patterns

### Pattern 1: Page Navigation Test

```typescript
test.describe('Navigation Tests', () => {
  test('should have visible skip link', async ({ page }) => {
    await page.goto('/');

    const skipLinks = await validateSkipLinks(page);
    expect(skipLinks.hasSkipLink).toBe(true);
    expect(skipLinks.skipLinks).toHaveLength(1);
  });

  test('should have valid tab order', async ({ page }) => {
    await page.goto('/');

    const tabOrder = await extractTabOrder(page);
    expect(tabOrder.length).toBeGreaterThan(0);
  });
});
```

### Pattern 2: Interactive Element Test

```typescript
test.describe('Button Accessibility', () => {
  test('should have accessible names', async ({ page }) => {
    await page.goto('/');

    const buttons = await validateButtonLabels(page);
    expect(buttons.allButtonsLabeled).toBe(true);
  });

  test('should have visible focus indicator', async ({ page }) => {
    await page.goto('/');

    const focus = await verifyFocusIndicators(page);
    expect(focus.elementsWithoutFocus).toBe(0);
  });
});
```

### Pattern 3: Contrast Test

```typescript
test.describe('Color Contrast Tests', () => {
  test('text should have 4.5:1 contrast', async ({ page }) => {
    await page.goto('/');

    const result = await testTextContrast(page, page.locator('body'), 'AA');
    expect(result.passes).toBe(true);
  });

  test('buttons should have 3:1 contrast', async ({ page }) => {
    await page.goto('/');

    const results = await testContrastBatch(page, 'button', 'AA', 'ui');
    expect(results.every((r) => r.passes)).toBe(true);
  });
});
```

## Testing Tips

### Debugging Failed Tests

```bash
# Run in debug mode
DEBUG=1 npx playwright test

# Run in UI mode
npx playwright test --ui

# Run with headed browser (see what's happening)
HEADED=1 npx playwright test main-page.spec.ts
```

### Slow Motion for Visibility

```bash
# Run tests slowly to see each action
npx playwright test --headed --slow-mo=1000
```

### Check What Utility Returns

```typescript
test('debug utility output', async ({ page }) => {
  await page.goto('/');

  const result = await validateFormLabels(page);

  // Log to see structure
  console.log('Result:', result);
  console.log('All labeled:', result.allLabeled);
  console.log('Unlabeled:', result.unlabeledElements);
});
```

### Screenshot Assertions

```typescript
test('page layout is correct', async ({ page }) => {
  await page.goto('/');

  // Capture screenshot for visual inspection
  await captureNormalState(page, page.locator('body'), '/tmp/page.png');

  // View in: /tmp/page.png
});
```

## Submission Checklist

Before submitting a PR with new tests:

- [ ] Tests follow naming conventions
- [ ] Code follows existing style
- [ ] Uses utility functions from `utils/index.js`
- [ ] Tests are focused on WCAG criteria
- [ ] Tests pass locally (run: `npm run test:ui:accessibility`)
- [ ] Tests pass on all browsers (run: `npm run test:ui:accessibility:all`)
- [ ] Added comments explaining what WCAG criteria are tested
- [ ] No `test.only()` or `test.skip()` in code
- [ ] Updated `COVERAGE.md` if adding new criteria
- [ ] Verified test with `--headed` mode
- [ ] No hardcoded timeouts (use `waitFor` instead)
- [ ] Handles both authenticated and public pages appropriately

### PR Description Template

````markdown
## What's being tested

- WCAG 2.1 criterion being tested
- Specific behavior or feature

## Files modified

- List of test files added/modified

## Testing instructions

```bash
npm run test:ui:accessibility
# or specific file
npx playwright test [filename].spec.ts
```
````

## Coverage updated

- [ ] Updated COVERAGE.md with new tests
- [ ] Updated README.md if major feature added

```

## Questions & Support

- Check existing tests in `tests/accessibility/*.spec.ts`
- Review utility documentation in `README.md`
- Ask in PR review or issues
- Check WCAG 2.1 guidelines: https://www.w3.org/WAI/WCAG21/quickref/
```
