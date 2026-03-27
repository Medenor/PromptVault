/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Button keyboard activation utility
 *
 * Adds support for activating buttons with Enter and Space keys.
 * This is essential for WCAG 2.1 AA compliance (2.1.1 Keyboard).
 *
 * When a button receives focus and the user presses:
 * - Enter key: Activates the button (simulates click)
 * - Space key: Activates the button (simulates click)
 *
 * This handler:
 * 1. Only works on button elements
 * 2. Respects disabled state (disabled buttons won't activate)
 * 3. Prevents default behavior to avoid double-submission
 * 4. Triggers the button's click handlers and form submission
 */

export function initButtonKeyboardActivation(): void {
  document.addEventListener('keydown', (event: KeyboardEvent) => {
    const target = event.target as HTMLElement | null;

    // Only process if target is a button element
    if (!target || !(target instanceof HTMLButtonElement)) {
      return;
    }

    // Skip disabled buttons
    if (target.disabled) {
      return;
    }

    // Check for Enter key (keyCode 13 or key === 'Enter')
    const isEnterKey = event.key === 'Enter' || event.keyCode === 13;

    // Check for Space key (keyCode 32 or key === ' ')
    const isSpaceKey = event.key === ' ' || event.keyCode === 32;

    if (!isEnterKey && !isSpaceKey) {
      return;
    }

    // Prevent default behavior
    // For Enter: prevents form submission if the button isn't a submit button
    // For Space: prevents page scrolling
    event.preventDefault();

    // Trigger the button's click event, which will:
    // 1. Call any onclick handlers
    // 2. Trigger form submission if button type is "submit"
    // 3. Call any click event listeners
    target.click();
  });
}
