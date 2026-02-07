# Comprehensive Manual Accessibility Testing Guide

This guide provides step-by-step instructions for performing manual accessibility testing on PromptVault to verify WCAG 2.1 AA compliance.

## 🎯 Testing Objectives

1. **Verify Keyboard Navigation** (T-ACC006)
2. **Test Screen Reader Compatibility** (T-ACC007)  
3. **Validate Color Contrast** (T-ACC026/27)
4. **Confirm Accessibility Features**

## 📋 Prerequisites

### Required Tools

- **Browsers**: Chrome, Firefox (latest versions)
- **Screen Readers**: 
  - macOS: VoiceOver (built-in)
  - Windows: NVDA (free) or JAWS
- **Color Tools**: WebAIM Contrast Checker, browser dev tools
- **Testing Environment**: Local development server running PromptVault

### Setup Instructions

1. **Start the application**:
   ```bash
   cd PromptVault
   # Start your development server (adjust command as needed)
   ```

2. **Prepare test accounts**:
   - Regular user account
   - Admin account
   - Ensure you can access all routes

3. **Install screen readers**:
   - macOS: VoiceOver is built-in (Cmd+F5 to toggle)
   - Windows: Download and install NVDA

## 🧪 Testing Methodology

### Test Approach

1. **Route-by-Route Testing**: Test each page systematically
2. **Component Testing**: Focus on interactive elements
3. **Scenario Testing**: Test complete user flows
4. **Edge Case Testing**: Test error states and special conditions

### Test Environment Matrix

| Browser | Screen Reader | OS | Responsibility |
|---------|---------------|----|----------------|
| Chrome | VoiceOver | macOS | Primary testing |
| Firefox | VoiceOver | macOS | Secondary verification |
| Chrome | NVDA | Windows | Cross-platform (if available) |

## 🗺️ Route Testing Checklist

### 1. Main Page (`/`)

#### Keyboard Navigation Test

1. **Skip Link Test**
   - [ ] Tab to skip link (should appear on first tab)
   - [ ] Press Enter - should focus main content
   - [ ] Verify focus styling is visible

2. **Header Navigation**
   - [ ] Tab through header elements (logo, navigation, user menu)
   - [ ] Verify logical tab order
   - [ ] Test dropdown menus with arrow keys

3. **Main Content**
   - [ ] Tab through all interactive elements
   - [ ] Test category/tag filters with keyboard
   - [ ] Verify focus traps don't exist

4. **Form Elements**
   - [ ] Test search input with keyboard
   - [ ] Verify Enter submits form
   - [ ] Test Escape cancels operations

#### Screen Reader Test

1. **Landmarks**
   - [ ] Verify banner, navigation, main roles are announced
   - [ ] Test landmark navigation (VoiceOver: Ctrl+Option+U)

2. **Interactive Elements**
   - [ ] Verify all buttons have accessible names
   - [ ] Test form labels and descriptions
   - [ ] Verify error messages are announced

3. **Dynamic Content**
   - [ ] Test live region announcements
   - [ ] Verify notifications are read automatically

#### Contrast Verification

1. **Text Elements**
   - [ ] Check primary text contrast (should be 4.5:1+)
   - [ ] Verify secondary text contrast
   - [ ] Check placeholder text contrast

2. **UI Components**
   - [ ] Verify button contrast
   - [ ] Check input border visibility
   - [ ] Test focus indicator contrast

### 2. Import/Export Page (`/import-export`)

#### Keyboard Navigation
- [ ] Test file upload with keyboard
- [ ] Verify form field navigation
- [ ] Test modal dialogs (Escape to close)

#### Screen Reader
- [ ] Verify file input labels
- [ ] Test progress announcements
- [ ] Check error message readability

#### Contrast
- [ ] Verify form field contrast
- [ ] Check button visibility
- [ ] Test status message contrast

### 3. Backup Management (`/backup-management`)

#### Keyboard Navigation
- [ ] Test form inputs and buttons
- [ ] Verify modal dialog keyboard support
- [ ] Test confirmation dialogs

#### Screen Reader
- [ ] Verify form field labels
- [ ] Test validation error announcements
- [ ] Check success message readability

#### Contrast
- [ ] Verify input field borders
- [ ] Check disabled button contrast
- [ ] Test warning/error message contrast

### 4. Authentication Pages

#### Login (`/auth/login`)
- [ ] Test form field navigation
- [ ] Verify error message focus
- [ ] Test password visibility toggle

#### Register (`/auth/register`)
- [ ] Test all form fields
- [ ] Verify validation messages
- [ ] Check password requirements

#### Forgot Password (`/auth/forgot-password`)
- [ ] Test email field
- [ ] Verify submission feedback
- [ ] Check error handling

#### Reset Password (`/auth/reset-password`)
- [ ] Test password fields
- [ ] Verify validation
- [ ] Check success message

#### Profile (`/auth/profile`)
- [ ] Test form field navigation
- [ ] Verify save functionality
- [ ] Check error handling

### 5. Category Management (`/manage-categories`)

#### Keyboard Navigation (Complex Component)
- [ ] Test roving tabindex in category list
- [ ] Verify arrow key navigation
- [ ] Test Home/End keys
- [ ] Check typeahead functionality
- [ ] Test merge/find/replace operations

#### Screen Reader
- [ ] Verify list item announcements
- [ ] Test operation feedback
- [ ] Check error message readability

#### Contrast
- [ ] Verify list item contrast
- [ ] Check operation button visibility
- [ ] Test form field contrast

### 6. Tag Management (`/manage-tags`)

#### Keyboard Navigation (Complex Component)
- [ ] Test roving tabindex in tag list
- [ ] Verify arrow key navigation
- [ ] Test Home/End keys
- [ ] Check typeahead functionality
- [ ] Test bulk operations

#### Screen Reader
- [ ] Verify tag announcements
- [ ] Test operation feedback
- [ ] Check error message readability

#### Contrast
- [ ] Verify tag visibility
- [ ] Check operation button contrast
- [ ] Test form field contrast

### 7. Admin Pages

#### Users (`/admin/users`)
- [ ] Test table navigation
- [ ] Verify row actions accessibility
- [ ] Check filter functionality
- [ ] Test pagination

#### Sessions (`/admin/sessions`)
- [ ] Test table navigation
- [ ] Verify session details
- [ ] Check termination functionality
- [ ] Test search/filter

## 🔍 Component-Specific Tests

### Category/Tag Filters (Roving Tabindex)

1. **Keyboard Navigation**
   - [ ] Tab to filter list
   - [ ] Use arrow keys to navigate items
   - [ ] Press Home/End to jump to first/last item
   - [ ] Press Enter/Space to select item
   - [ ] Type letters for typeahead navigation
   - [ ] Verify focus styling is visible

2. **Screen Reader**
   - [ ] Verify item announcements
   - [ ] Test selected state announcement
   - [ ] Check operation feedback

### Admin Tables

1. **Keyboard Navigation**
   - [ ] Tab through table headers
   - [ ] Navigate to table cells
   - [ ] Test row action buttons
   - [ ] Verify pagination controls
   - [ ] Check sort functionality

2. **Screen Reader**
   - [ ] Verify table structure announcement
   - [ ] Test cell associations with headers
   - [ ] Check row action accessibility

## 🎨 Color Contrast Testing

### Manual Contrast Verification

1. **Primary Text**
   - Check all main text elements
   - Verify 4.5:1 minimum contrast
   - Use WebAIM Contrast Checker

2. **Secondary Text**
   - Check help text, labels, descriptions
   - Verify 4.5:1 minimum contrast
   - Pay special attention to gray text

3. **UI Components**
   - Buttons: 4.5:1 text contrast, 3:1 border contrast
   - Input fields: 3:1 border contrast
   - Focus indicators: 3:1 contrast against background

4. **Status Indicators**
   - Error messages: 4.5:1 contrast
   - Warning messages: 4.5:1 contrast  
   - Success messages: 4.5:1 contrast

### Specific Elements to Check

| Element | Expected Contrast | Test Method |
|---------|-------------------|-------------|
| Main text on white | 21:1 | Visual + tool verification |
| Secondary text | 5.6:1+ | Tool verification |
| Warning text | 4.8:1+ | Tool verification |
| Disabled text | 5.5:1+ | Tool verification |
| Input borders | 3.8:1+ | Tool verification |
| Focus rings | 6.2:1+ | Visual verification |

## 📝 Test Reporting Template

### Manual Testing Report

**Tester Name**: _______________________  
**Date**: _______________________  
**Browser/OS**: _______________________  
**Screen Reader**: _______________________  

#### Route: `/` (Main Page)

**Keyboard Navigation**
- [ ] Skip link works correctly
- [ ] Tab order is logical
- [ ] No keyboard traps
- [ ] Focus always visible
- [ ] All controls keyboard-operable
- [ ] Escape closes modals/menus
- [ ] Disabled elements not focusable
- **Issues Found**: _______________________

**Screen Reader**
- [ ] Page has appropriate title
- [ ] Landmarks are usable
- [ ] Buttons/links have accessible names
- [ ] Fields have proper labels
- [ ] Errors are announced
- [ ] Notifications are announced
- **Issues Found**: _______________________

**Contrast**
- [ ] Primary text contrast sufficient
- [ ] Secondary text contrast sufficient
- [ ] UI component contrast sufficient
- [ ] Focus indicators visible
- **Issues Found**: _______________________

#### Route: `/import-export`

**Keyboard Navigation**
- [ ] File upload works with keyboard
- [ ] Form navigation logical
- [ ] Modal dialogs keyboard-accessible
- **Issues Found**: _______________________

**Screen Reader**
- [ ] File input properly labeled
- [ ] Progress announcements work
- [ ] Error messages readable
- **Issues Found**: _______________________

**Contrast**
- [ ] Form fields have sufficient contrast
- [ ] Buttons visible
- [ ] Status messages readable
- **Issues Found**: _______________________

*(Continue this pattern for all routes)*

## 🛠️ Testing Tools Guide

### Keyboard Testing

**Essential Shortcuts**
- `Tab`: Move focus forward
- `Shift+Tab`: Move focus backward
- `Enter`: Activate buttons/links
- `Space`: Toggle checkboxes/buttons
- `Escape`: Close modals/dialogs
- `Arrow Keys`: Navigate within components
- `Home/End`: Jump to first/last item

### Screen Reader Commands

**VoiceOver (macOS)**
- `Ctrl+Option+U`: Landmarks navigation
- `Ctrl+Option+Right/Left`: Navigate between elements
- `Ctrl+Option+Space`: Activate element
- `Ctrl+Option+Shift+Down`: Read from current position
- `VO+F`: Forms mode

**NVDA (Windows)**
- `Insert+F7`: Elements list
- `Insert+F5`: Forms mode
- `Insert+Space`: Toggle forms mode
- `Insert+T`: Read title
- `Insert+1`: Read current line

### Contrast Checking

**WebAIM Contrast Checker**
1. Open tool in browser
2. Enter foreground and background colors
3. Verify contrast ratio meets requirements
4. Document any failures

**Browser DevTools**
1. Inspect element
2. Check computed colors
3. Use color picker for contrast analysis
4. Note any insufficient contrast

## 📊 Severity Classification

| Severity | Definition | Example |
|----------|------------|---------|
| **Blocker** | Prevents task completion | Keyboard trap, unreadable text |
| **Critical** | Major accessibility barrier | Missing labels, broken navigation |
| **High** | Significant issue | Poor contrast, missing landmarks |
| **Medium** | Noticeable issue | Suboptimal tab order, minor contrast |
| **Low** | Cosmetic issue | Inconsistent styling, minor announcements |

## 🎯 Test Completion Checklist

- [ ] All routes tested for keyboard navigation
- [ ] All routes tested with screen reader
- [ ] Color contrast verified for all components
- [ ] Complex components tested thoroughly
- [ ] Error states and edge cases tested
- [ ] Mobile responsiveness verified
- [ ] Test report completed with findings
- [ ] Issues prioritized by severity
- [ ] Recommendations documented

## 💡 Testing Tips

1. **Test in Multiple Browsers**: Chrome and Firefox may behave differently
2. **Use Real Screen Readers**: Don't rely solely on automated tools
3. **Test Error States**: Don't just test happy paths
4. **Verify Focus Management**: Ensure focus doesn't get lost
5. **Check Mobile Behavior**: Test on smaller viewports
6. **Document Everything**: Note even minor issues
7. **Be Thorough**: Test all interactive elements
8. **Take Breaks**: Screen reader testing can be fatiguing

## 📚 Additional Resources

- **WCAG 2.1 Guidelines**: https://www.w3.org/WAI/WCAG21/quickref/
- **WebAIM Resources**: https://webaim.org/resources/
- **ARIA Authoring Practices**: https://www.w3.org/TR/wai-aria-practices/
- **Keyboard Navigation Patterns**: https://www.w3.org/WAI/ARIA/apg/patterns/

## 🎉 Testing Complete!

Once all testing is complete:

1. **Review findings** with the development team
2. **Prioritize fixes** based on severity
3. **Create tickets** for identified issues
4. **Schedule retesting** after fixes are implemented
5. **Document lessons learned** for future reference

This comprehensive testing will ensure PromptVault meets WCAG 2.1 AA standards and provides an accessible experience for all users!