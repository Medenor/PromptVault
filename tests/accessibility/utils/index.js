// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Accessibility testing utilities index
 * Central export point for all accessibility testing helper functions
 */

// Contrast utilities
export {
  parseColor,
  calculateRelativeLuminance,
  calculateContrastRatio,
  isContrastCompliant,
  getElementColors,
  getEffectiveBackgroundColor,
  testTextContrast,
  testUIContrast,
  testContrastBatch,
} from './contrast.js';

// ARIA utilities
export {
  checkAccessibleName,
  validateAriaAttributes,
  checkLandmarkRegions,
  validateFormLabels,
  checkLiveRegions,
  validateButtonLabels,
  validateHeadingHierarchy,
  getAriaAttributes,
  validateAccessibleNamesBatch,
} from './aria.js';

// Keyboard utilities
export {
  extractTabOrder,
  testKeyboardNavigation,
  verifyFocusIndicators,
  testKeyboardShortcuts,
  testBackwardNavigation,
  validateRovingTabindex,
  testKeyActivation,
  validateSkipLinks,
} from './keyboard.js';

// Screenshot utilities
export {
  captureNormalState,
  captureHoverState,
  captureFocusState,
  captureActiveState,
  captureErrorState,
  captureDisabledState,
  captureElementStates,
  compareFocusIndicators,
  capturePageWithHighlight,
  captureMultipleElements,
  captureFocusVisible,
  createStateComparisonGrid,
} from './screenshots.js';
