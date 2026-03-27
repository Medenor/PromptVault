# PromptVault Color Palette - WCAG AA Compliance Reference

## Overview
This document provides a complete reference of all colors used in PromptVault and their WCAG AA compliance status.

---

## Primary Color System (Blues)

### Current Palette
| Shade | Hex Value | RGB | Use Cases |
|-------|-----------|-----|-----------|
| primary-50 | `#eff6ff` | (239, 246, 255) | Light backgrounds, hover states |
| primary-100 | `#dbeafe` | (219, 234, 254) | Light backgrounds, status messages |
| primary-200 | `#bfdbfe` | (191, 219, 254) | Light backgrounds, borders |
| primary-300 | `#93c5fd` | (147, 197, 253) | Light backgrounds |
| primary-400 | `#60a5fa` | (96, 165, 250) | Accents, minor elements |
| primary-500 | `#3b82f6` | (59, 130, 246) | **⚠️ FAILS** - Header text, Links |
| primary-600 | `#2563eb` | (37, 99, 235) | Buttons, hover states |
| primary-700 | `#1d4ed8` | (29, 78, 216) | **✓ RECOMMENDED** - Headers, Links |
| primary-800 | `#1e40af` | (30, 64, 175) | Dark text, active states |
| primary-900 | `#1e3a8a` | (30, 58, 138) | Very dark text, focus indicators |

### What Changed?
- **OLD**: primary-500 (#3b82f6) → **NEW**: primary-700 (#1d4ed8)
- **Reason**: Darker color provides better contrast with white text
- **Compliance**: 3.68:1 → 6.70:1

---

## Secondary Color System (Green/Emerald)

### Current Palette
| Shade | Hex Value | RGB | Use Cases |
|-------|-----------|-----|-----------|
| secondary-50 | `#ecfdf5` | (236, 253, 245) | Light backgrounds |
| secondary-100 | `#d1fae5` | (209, 250, 229) | Light backgrounds |
| secondary-200 | `#a7f3d0` | (167, 243, 208) | Light backgrounds |
| secondary-300 | `#6ee7b7` | (110, 231, 183) | Accents |
| secondary-400 | `#34d399` | (52, 211, 153) | Accents |
| secondary-500 | `#10b981` | (16, 185, 129) | **⚠️ FAILS** - Green buttons with white text |
| secondary-600 | `#059669` | (5, 150, 105) | Button hover states |
| secondary-700 | `#047857` | (4, 120, 87) | **✓ RECOMMENDED** - Button backgrounds |
| secondary-800 | `#065f46` | (6, 95, 70) | Dark buttons, focus states |
| secondary-900 | `#064e3b` | (6, 78, 59) | Very dark elements |

### What Changed?
- **OLD**: secondary-500 (#10b981) → **NEW**: secondary-700 (#047857)
- **Reason**: Worst failure (2.54:1) - needed darkest shade for white text
- **Compliance**: 2.54:1 → 4.92:1

---

## Accent Color System (Amber/Yellow)

### Current Palette
| Shade | Hex Value | RGB | Use Cases |
|-------|-----------|-----|-----------|
| accent-50 | `#fffbeb` | (255, 251, 235) | Light backgrounds, alerts |
| accent-100 | `#fef3c7` | (254, 243, 199) | Light backgrounds |
| accent-200 | `#fde68a` | (253, 230, 138) | Light backgrounds |
| accent-300 | `#fcd34d` | (252, 211, 77) | Accents |
| accent-400 | `#fbbf24` | (251, 191, 36) | Accents, warnings |
| accent-500 | `#f59e0b` | (245, 158, 11) | Accents |
| accent-600 | `#d97706` | (217, 119, 6) | **⚠️ FAILS** - Buttons, warning text |
| accent-700 | `#b45309` | (180, 83, 9) | **✓ RECOMMENDED** - Button backgrounds |
| accent-800 | `#92400e` | (146, 64, 14) | Dark accents |
| accent-900 | `#78350f` | (120, 53, 15) | **✓ RECOMMENDED** - Warning text |

### What Changed?
- **Buttons**: accent-600 (#d97706) → **accent-700** (#b45309) - 3.19:1 → 4.57:1
- **Warning Text**: accent-600 (#d97706) → **accent-900** (#78350f) - 3.19:1 → 8.75:1
- **Reason**: Lighter shade fails for button text; darker shade recommended for text

---

## Cyan Color System

### Current Palette
| Shade | Hex Value | RGB | Use Cases |
|-------|-----------|-----|-----------|
| cyan-50 | `#ecfdfd` | (236, 253, 253) | Light backgrounds |
| cyan-100 | `#cff9fc` | (207, 249, 252) | Light backgrounds |
| cyan-200 | `#a5f3fc` | (165, 243, 252) | Light backgrounds |
| cyan-300 | `#67e8f9` | (103, 232, 249) | Accents |
| cyan-400 | `#22d3ee` | (34, 211, 238) | Accents |
| cyan-500 | `#06b6d4` | (6, 182, 212) | Accents |
| cyan-600 | `#0891b2` | (8, 145, 178) | **⚠️ FAILS** - Button backgrounds with white text |
| cyan-700 | `#0e7490` | (14, 116, 144) | **✓ RECOMMENDED** - Button backgrounds |
| cyan-800 | `#155e75` | (21, 94, 117) | Dark buttons |
| cyan-900 | `#164e63` | (22, 78, 99) | Very dark elements |

### What Changed?
- **OLD**: cyan-600 (#0891b2) → **NEW**: cyan-700 (#0e7490)
- **Reason**: Better contrast with white text for buttons
- **Compliance**: 3.68:1 → 5.09:1

---

## Gray Scale (Neutral)

### Current Palette
| Shade | Hex Value | RGB | Use Cases | Compliance |
|-------|-----------|-----|-----------|------------|
| gray-50 | `#f9fafb` | (249, 250, 251) | Backgrounds | ✓ Excellent |
| gray-100 | `#f3f4f6` | (243, 244, 246) | Hover backgrounds | ✓ Excellent |
| gray-200 | `#e5e7eb` | (229, 231, 235) | Borders, backgrounds | ✓ Excellent |
| gray-300 | `#d1d5db` | (209, 213, 219) | Borders | ✓ Excellent |
| gray-400 | `#9ca3af` | (156, 163, 175) | Icons, borders | ✓ Good |
| gray-500 | `#6b7280` | (107, 114, 128) | Secondary text | ✓ Good |
| gray-600 | `#4b5563` | (75, 85, 99) | Body text | ✓ Excellent |
| gray-700 | `#374151` | (55, 65, 81) | Body text | ✓ Excellent |
| gray-800 | `#1f2937` | (31, 41, 55) | Headings | ✓ Excellent |
| gray-900 | `#111827` | (17, 24, 39) | Dark text | ✓ Excellent |

**Status**: All gray combinations PASS ✓

---

## Red Colors (Errors)

| Shade | Hex Value | RGB | Use Cases | Compliance |
|-------|-----------|-----|-----------|------------|
| red-50 | `#fef2f2` | (254, 242, 242) | Error backgrounds | ✓ Good |
| red-100 | `#fee2e2` | (254, 226, 226) | Error containers | ✓ Good |
| red-600 | `#dc2626` | (220, 38, 38) | Error buttons | ✓ Good |
| red-700 | `#b91c1c` | (185, 28, 28) | Dark error | ✓ Good |
| red-900 | `#7f1d1d` | (127, 29, 29) | Very dark error | ✓ Good |

**Status**: All red combinations PASS ✓

---

## Reference: Contrast Ratio Calculation

### Formula Used (WCAG 2.1)
```
Contrast Ratio = (L1 + 0.05) / (L2 + 0.05)

Where:
L = (0.2126 * R + 0.7152 * G + 0.0722 * B) with gamma adjustment

Requirements:
- WCAG AA: >= 4.5:1 for normal text
- WCAG AAA: >= 7.0:1 for normal text
```

### Interpretation
| Ratio | Grade | Usability |
|-------|-------|-----------|
| < 3.0:1 | FAIL | Very difficult to read |
| 3.0-4.5:1 | BORDERLINE | Difficult for some users |
| 4.5-7.0:1 | PASS AA | Good readability |
| > 7.0:1 | PASS AAA | Excellent readability |

---

## Usage Guidelines

### Headers (White Text)
- ✓ Use: `#1d4ed8` (blue-700) or darker
- ✗ Avoid: `#3b82f6` (blue-500) - only 3.68:1

### Links (On White Backgrounds)
- ✓ Use: `#1d4ed8` (blue-700) or darker
- ✗ Avoid: `#3b82f6` (blue-500) - only 3.68:1

### Success/Green Buttons (White Text)
- ✓ Use: `#047857` (emerald-700) or darker
- ✗ Avoid: `#10b981` (emerald-500) - only 2.54:1

### Warning/Amber Text (On White)
- ✓ Use: `#78350f` (amber-900) for excellent readability
- ~ Use: `#b45309` (amber-700) for adequate readability
- ✗ Avoid: `#d97706` (amber-600) - only 3.19:1

### Warning/Amber Buttons (White Text)
- ✓ Use: `#b45309` (amber-700) or darker
- ✗ Avoid: `#d97706` (amber-600) - only 3.19:1

### Cyan Buttons (White Text)
- ✓ Use: `#0e7490` (cyan-700) or darker
- ✗ Avoid: `#0891b2` (cyan-600) - only 3.68:1

---

## CSS Class Mapping

### Color Classes to Update
```css
/* Headers */
.bg-blue-500 → .bg-blue-700
header.bg-blue-500 → header.bg-blue-700

/* Links */
a { color: #3b82f6; } → a { color: #1d4ed8; }

/* Buttons */
.bg-emerald-500.text-white → .bg-emerald-700.text-white
.bg-amber-600.text-white → .bg-amber-700.text-white
.bg-cyan-600.text-white → .bg-cyan-700.text-white

/* Text */
.text-amber-600 → .text-amber-900 (for warnings)
```

---

## Testing Tools & Resources

### Browser Extensions
- **Stark**: Real-time contrast checking
- **Color Contrast Analyzer**: Standalone tool
- **axe DevTools**: Automated accessibility checks
- **WAVE**: Web accessibility evaluation

### Online Tools
- **WebAIM Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **Accessible Colors**: https://accessible-colors.com/
- **Contrast Ratio**: https://contrast-ratio.com/

### Documentation
- **WCAG 2.1 Contrast**: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html
- **Color Blindness Simulator**: https://www.color-blindness.com/

---

## Implementation Summary

### Changes Required
| Element | Current Color | New Color | File(s) |
|---------|---------------|-----------|---------|
| Header BG | `#3b82f6` | `#1d4ed8` | 7 template files |
| Link Color | `#3b82f6` | `#1d4ed8` | tailwind-globals.css |
| Green Button | `#10b981` | `#047857` | index.html |
| Amber Button | `#d97706` | `#b45309` | backup_management.html |
| Cyan Button | `#0891b2` | `#0e7490` | backup_management.html |
| Warning Text | `#d97706` | `#78350f` | tailwind-globals.css |

### Estimated Impact
- **Files to Update**: 9
- **Lines to Change**: ~15
- **Implementation Time**: 30 minutes
- **Testing Time**: 1-2 hours
- **User Impact**: Positive (better readability)

---

## Dark Mode Considerations

For future dark mode implementation:
- Dark backgrounds will require lighter text colors
- Current light backgrounds (gray-50, etc.) will need dark equivalents
- Recommend testing all combinations against dark backgrounds
- Consider using CSS custom properties for easy theme switching

---

## Accessibility Checklist

After implementing color changes:
- [ ] Run WebAIM Contrast Checker on all pages
- [ ] Test with Chrome DevTools Accessibility Audit
- [ ] Verify with 3rd party tool (axe, WAVE)
- [ ] Manual testing with real users
- [ ] Screen reader testing
- [ ] Keyboard navigation testing
- [ ] Test on mobile devices
- [ ] Verify print styles (if applicable)

---

## Questions & Support

For questions about:
- **WCAG Standards**: Visit https://www.w3.org/WAI/
- **Implementation Help**: See CONTRAST_FIXES_IMPLEMENTATION.md
- **Detailed Analysis**: See WCAG_AA_CONTRAST_ANALYSIS_REPORT.md
- **Quick Summary**: See CONTRAST_ANALYSIS_SUMMARY.txt

---

**Document Version**: 1.0
**Last Updated**: February 2026
**Status**: Ready for Implementation
**Reviewer**: Accessibility Team
