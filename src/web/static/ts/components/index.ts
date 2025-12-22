/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Component Library - Central Export
 * Allows imports like: import { createButton } from '@components'
 */

// Export all types
export * from './types.js';

// Export button components
export {
  createButton,
  createPrimaryButton,
  createSecondaryButton,
  createAccentButton,
  createGhostButton,
  createDangerButton,
} from './button.js';

// Export card components
export {
  createCard,
  createWhiteCard,
  createColoredCard,
  createElevatedCard,
  createBorderedCard,
} from './card.js';

// Export input components
export {
  createInput,
  createTextarea,
  createEmailInput,
  createPasswordInput,
  createSearchInput,
  createNumberInput,
  createDateInput,
  createFileInput,
} from './input.js';

// Export form components
export {
  createFormGroup,
  createLabeledInput,
  createSelectInput,
  createCheckbox,
  createRadioGroup,
} from './form.js';

// Export modal components
export { createModal, createConfirmModal, createAlertModal } from './modal.js';

// Export layout components
export {
  createContainer,
  createSection,
  createFlex,
  createGrid,
  createHeader,
  createFooter,
} from './layout.js';

// Export navigation components
export { createNav, createTabs, createBreadcrumbs } from './navigation.js';
