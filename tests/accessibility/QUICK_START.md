# Accessibility Testing - Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies (Already Done)
```bash
npm install  # Playwright is already installed
```

### 2. Run Existing Tests
```bash
# Run accessibility tests on chromium
npm run test:ui:accessibility

# Run on all browsers
npm run test:ui:accessibility:all

# Run in debug mode (see browser window)
HEADED=1 npm run test:ui:accessibility
```

## Writing Your First Test

### Simple Page Test
```javascript
import { test, expect } from '@playwright/test';
import { validateFormLabels, testTextContrast } from '../accessibility/utils/index.js';

test('home page is accessible', async ({ page }) => {
  await page.goto('/');

  // Check all form inputs have labels
  const labels = await validateFormLabels(page);
  expect(labels.allLabeled).toBe(true);

  // Check text contrast
  const h1 = page.locator('h1');
  const contrast = await testTextContrast(page, h1, 'AA');
  expect(contrast.passes).toBe(true);
});
```

### Authenticated Page Test
```javascript
import { authenticatedUserTest } from '../accessibility/fixtures/index.js';
import { validateFormLabels } from '../accessibility/utils/index.js';

authenticatedUserTest('profile page is accessible', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/auth/profile');

  const labels = await validateFormLabels(authenticatedPage);
  expect(labels.allLabeled).toBe(true);
});
```

### Keyboard Navigation Test
```javascript
import { testKeyboardNavigation, verifyFocusIndicators } from '../accessibility/utils/index.js';

test('form is keyboard accessible', async ({ page }) => {
  await page.goto('/auth/login');

  // Test Tab navigation works
  const nav = await testKeyboardNavigation(page);
  expect(nav.success).toBe(true);

  // Verify focus is visible
  const focus = await verifyFocusIndicators(page);
  expect(focus.elementsWithoutFocus).toBe(0);
});
```

## Common Utility Functions

### Contrast Testing
```javascript
import { testTextContrast, testUIContrast } from '../accessibility/utils/index.js';

// Text contrast (4.5:1 for AA)
const result = await testTextContrast(page, page.locator('p'), 'AA');
console.log(result.ratio, result.passes);

// UI contrast (3:1 for AA)
const btnResult = await testUIContrast(page, page.locator('button'), 'AA');
```

### Form & Button Validation
```javascript
import { validateFormLabels, validateButtonLabels } from '../accessibility/utils/index.js';

// Check all inputs have labels
const forms = await validateFormLabels(page);
console.log(forms.allLabeled, forms.unlabeledElements);

// Check all buttons have accessible names
const buttons = await validateButtonLabels(page);
console.log(buttons.allButtonsLabeled);
```

### Structure & Semantics
```javascript
import {
  checkLandmarkRegions,
  validateHeadingHierarchy
} from '../accessibility/utils/index.js';

// Check for header, main, footer, nav
const landmarks = await checkLandmarkRegions(page);
console.log(landmarks.landmarks); // [{role: 'banner', count: 1}, ...]

// Check H1, H2, H3... don't skip levels
const hierarchy = await validateHeadingHierarchy(page);
console.log(hierarchy.validHierarchy, hierarchy.issues);
```

### Keyboard Navigation
```javascript
import { extractTabOrder, verifyFocusIndicators } from '../accessibility/utils/index.js';

// Get focusable elements in tab order
const tabOrder = await extractTabOrder(page);
console.log(tabOrder); // [{selector, text, tabIndex, isNaturallyFocusable}, ...]

// Verify focus indicators are visible
const focus = await verifyFocusIndicators(page);
console.log(focus.elementsWithoutFocus); // Should be 0
```

### Screenshots
```javascript
import { captureElementStates } from '../accessibility/utils/index.js';

// Capture button in all states
const states = await captureElementStates(page, page.locator('button'), '/tmp/btn');
// Returns: { normal, hover, focus, active }
```

## Environment Variables

### For Local Testing
```bash
# Use default local server
npm run test:ui:accessibility

# Use custom server
ACCESSIBILITY_BASE_URL=http://localhost:3000 npm run test:ui:accessibility

# Run in headed mode (see browser)
HEADED=1 npm run test:ui:accessibility
```

### For Testing Protected Pages
```bash
# With credentials (will login)
ACCESSIBILITY_USER_USERNAME=test@example.com \
ACCESSIBILITY_USER_PASSWORD=password123 \
npm run test:ui:accessibility

# Or reuse saved auth state (faster)
ACCESSIBILITY_AUTH_STATE_DIR=/tmp/pw-auth \
npm run test:ui:accessibility
```

### For CI/CD
```bash
# Run on single browser, use cached state
ACCESSIBILITY_AUTH_STATE_DIR=/tmp/auth \
CI=1 \
npm run test:ui:accessibility
```

## Debugging

### See Browser Window
```bash
HEADED=1 npm run test:ui:accessibility
```

### Debug Mode (Pause on Test)
```bash
DEBUG=1 npm run test:ui:accessibility
```

### Run Specific Test
```bash
npx playwright test --grep "specific test name"
```

### Check What Was Tested
```bash
# View HTML report
open playwright-report/index.html
```

## WCAG Quick Reference

### Contrast Ratios Required (WCAG 2.1)

| Type | AA | AAA |
|------|----|----|
| Regular text | 4.5:1 | 7:1 |
| Large text (18pt+) | 3:1 | 4.5:1 |
| UI components | 3:1 | 4.5:1 |

### Key WCAG Success Criteria

- **1.4.3**: Color contrast (tested by our tools)
- **2.1**: Keyboard accessible (tested by our tools)
- **2.4**: Focus visible (tested by our tools)
- **3.2.4**: Labels/instructions (tested by our tools)
- **4.1.2**: Name, role, value (tested partially)

## Troubleshooting

### "Login failed" when running tests
```bash
# Set credentials
ACCESSIBILITY_USER_USERNAME=user@example.com \
ACCESSIBILITY_USER_PASSWORD=password \
npm run test:ui:accessibility

# Or create saved state first
ACCESSIBILITY_USER_USERNAME=user@example.com \
ACCESSIBILITY_USER_PASSWORD=password \
ACCESSIBILITY_AUTH_STATE_DIR=/tmp/auth \
npm run test:ui:accessibility
```

### "Element not found"
- Check selector is correct: `await page.locator('selector').count()`
- Make sure page loaded: `await page.waitForLoadState('networkidle')`

### "Focus indicator not visible"
- Make sure you're testing correct element
- Some elements have focus on child (e.g., input inside label)
- CSS might hide focus: check `:focus { outline: none }`

### Tests timing out
- Default is 60 seconds (see `playwright.config.ts`)
- Increase if needed: `test.setTimeout(120000)`
- Check if server is running: `http://localhost:8003`

## File Organization

```
tests/accessibility/
├── utils/                # All utility functions
│   ├── contrast.js      # Color contrast
│   ├── aria.js          # ARIA validation
│   ├── keyboard.js      # Keyboard testing
│   ├── screenshots.js   # Screenshots
│   └── index.js         # Import from here
├── fixtures/            # Fixtures and helpers
│   ├── auth.js          # Authentication
│   └── index.js         # Import from here
├── reports/             # Report templates
├── README.md            # Full documentation
├── IMPLEMENTATION.md    # Implementation details
└── QUICK_START.md       # This file
```

## Next Steps

1. **Read the full README** for comprehensive documentation
2. **Copy `sample-test.example.ts`** patterns for your tests
3. **Run tests regularly** during development
4. **Check reports** at `playwright-report/index.html`
5. **Extend utilities** as needed for your project

## Support

For detailed documentation:
- **Full guide**: See `README.md`
- **Function reference**: See `README.md#utilities`
- **Examples**: See `sample-test.example.ts`
- **Implementation details**: See `IMPLEMENTATION.md`

For Playwright help:
- [Playwright Documentation](https://playwright.dev)
- [Playwright Inspector](https://playwright.dev/docs/inspector)

For WCAG guidelines:
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
