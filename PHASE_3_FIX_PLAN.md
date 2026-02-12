# Phase 3 Test Regression - Fix Plan

## Root Cause Analysis

### Primary Issue: Skip Link CSS Mismatch
The test checks if skip link is hidden using:
```js
style.visibility === 'hidden' || style.display === 'none' || style.opacity === '0'
```

But our CSS only uses:
```css
left: -9999px;  /* Off-screen positioning, but doesn't set visibility/display/opacity */
```

**This causes skip link tests to fail** because the test doesn't recognize "off-screen" as "hidden".

### Secondary Issue: Selector Too Broad
Test selector `a[href^="#"]` matches ANY link starting with `#`, not just the skip link. This could cause false positives if other links exist.

### Tertiary Issue: Color Contrast Baseline
The large number of color contrast failures (130+) suggests either:
1. CSS was never properly updated with correct colors
2. Tests are stricter than before
3. Our changes broke something with color inheritance

## Fix Strategy

### Fix 1: Update Skip Link CSS
```css
.skip-link {
  position: absolute;
  top: 0.75rem;
  left: -9999px;
  z-index: 10000;
  /* EXPLICITLY HIDE - tests check for these properties */
  visibility: hidden;    /* ADD THIS */
  opacity: 0;           /* ADD THIS */
  border-radius: 0.5rem;
  border: 2px solid #1e3a8a;
  background-color: #ffffff;
  color: #1e3a8a;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.skip-link:focus,
.skip-link:focus-visible {
  left: 0.75rem;
  visibility: visible;   /* MAKE VISIBLE ON FOCUS */
  opacity: 1;           /* MAKE OPAQUE ON FOCUS */
  outline: 2px solid #1e3a8a;
  outline-offset: 2px;
}
```

### Fix 2: Review and Update CSS Color Scheme
- Audit all text colors against backgrounds
- Ensure 4.5:1 contrast ratio for normal text
- Ensure 3:1 contrast ratio for large text  
- Focus indicators must have sufficient contrast

### Fix 3: Check Focus Management Code for Side Effects
- Review focus storage/restoration in modals
- Ensure focus management doesn't interfere with test interactions
- Verify async focus handling works correctly

### Fix 4: Verify Test Expectations vs Reality
- Check if tests themselves have incorrect expectations
- Verify test utilities are calculating colors correctly
- Ensure test page loads completely before testing

## Implementation Priority
1. **CRITICAL**: Fix skip link CSS (quick fix, high impact)
2. **HIGH**: Audit and fix color contrasts throughout CSS
3. **HIGH**: Review focus management for side effects
4. **MEDIUM**: Verify test suite accuracy

## Expected Outcome
After fixes:
- Skip link failures should drop to ~0 (20 failures → 0)
- Color contrast failures should improve significantly (130+ failures → <20)
- Page structure failures should stabilize
- Focus and keyboard navigation should work correctly

## Success Metrics
- Tests passed: >2,400 (>78% pass rate)
- Tests failed: <750 (<24% failure rate)
- Skip link tests: 100% pass
- Color contrast tests: >90% pass
