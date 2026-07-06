/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Keyboard navigation and focus management utilities for WCAG 2.1 AA compliance
 * Handles:
 * - Logical tab order (top-to-bottom, left-to-right)
 * - Modal focus trapping
 * - Escape key handling
 * - Focus restoration
 */

/**
 * Focus trap state tracker
 */
interface FocusTrapState {
  element: HTMLElement;
  previousFocus: HTMLElement | null;
  firstFocusable: HTMLElement | null;
  lastFocusable: HTMLElement | null;
  handlers: {
    keydown: (e: Event) => void;
  };
}

const focusTrapStack: FocusTrapState[] = [];

/**
 * Get all focusable elements within a container in DOM order
 * This maintains logical tab order (top-to-bottom, left-to-right)
 */
export function getFocusableElements(
  container: HTMLElement,
  options?: { excludeDisabled?: boolean }
): HTMLElement[] {
  const focusableSelectors = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ];

  const focusables = Array.from(
    container.querySelectorAll<HTMLElement>(focusableSelectors.join(','))
  );

  // Filter out hidden elements and elements outside the container
  return focusables.filter((el) => {
    // Check if element is visible
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') {
      return false;
    }

    // Check if element is disabled
    if (options?.excludeDisabled && (el as HTMLInputElement).disabled) {
      return false;
    }

    // Ensure element is contained
    return container.contains(el);
  });
}

/**
 * Create a focus trap for a modal or dialog
 * Ensures Tab/Shift+Tab cycles only within the element
 */
export function createFocusTrap(
  element: HTMLElement,
  options?: { manageFocus?: boolean }
): {
  activate: () => void;
  deactivate: () => void;
  moveFocusToFirst: () => void;
} {
  let state: FocusTrapState | null = null;
  const manageFocus = options?.manageFocus !== false; // Default to true for backward compatibility

  const keydownHandler = (e: Event) => {
    const ke = e as KeyboardEvent;
    if (ke.key !== 'Tab' || !state) return;

    const focusables = getFocusableElements(element);
    if (focusables.length === 0) {
      ke.preventDefault();
      return;
    }

    const currentFocus = document.activeElement as HTMLElement | null;
    if (!currentFocus) return;

    const currentIndex = focusables.indexOf(currentFocus);

    if (ke.shiftKey) {
      // Shift+Tab - move backward
      if (currentIndex <= 0) {
        ke.preventDefault();
        const last = focusables[focusables.length - 1];
        if (last) last.focus();
      }
    } else {
      // Tab - move forward
      if (currentIndex >= focusables.length - 1) {
        ke.preventDefault();
        const first = focusables[0];
        if (first) first.focus();
      }
    }
  };

  return {
    activate: () => {
      // Store current focus to restore later (only if manageFocus is enabled)
      const previousFocus =
        manageFocus && document.activeElement instanceof HTMLElement
          ? document.activeElement
          : null;

      // Get all focusable elements
      const focusables = getFocusableElements(element);

      state = {
        element,
        previousFocus,
        firstFocusable: focusables[0] || null,
        lastFocusable: focusables[focusables.length - 1] || null,
        handlers: { keydown: keydownHandler },
      };

      // Add to stack for nested modals
      focusTrapStack.push(state);

      // Attach keydown listener
      document.addEventListener('keydown', keydownHandler, true);

      // Move focus to first element
      if (focusables.length > 0) {
        const first = focusables[0];
        if (first) first.focus();
      } else {
        // If no focusable elements, make container focusable
        element.setAttribute('tabindex', '-1');
        element.focus();
      }
    },

    deactivate: () => {
      if (!state) return;

      // Remove from stack
      const index = focusTrapStack.indexOf(state);
      if (index > -1) {
        focusTrapStack.splice(index, 1);
      }

      // Remove keydown listener
      document.removeEventListener('keydown', keydownHandler, true);

      // Restore focus to trigger element (only if manageFocus is enabled)
      if (manageFocus && state.previousFocus && state.previousFocus.isConnected) {
        state.previousFocus.focus();
      }

      // If there's another trap on the stack, reactivate it
      if (focusTrapStack.length > 0) {
        const previousTrap = focusTrapStack[focusTrapStack.length - 1];
        if (previousTrap && previousTrap.firstFocusable) {
          previousTrap.firstFocusable.focus();
        }
      }

      state = null;
    },

    moveFocusToFirst: () => {
      const focusables = getFocusableElements(element);
      if (focusables.length > 0) {
        const first = focusables[0];
        if (first) first.focus();
      } else {
        element.focus();
      }
    },
  };
}

/**
 * Handle Escape key to close modals
 * Returns true if event was handled
 */
export function handleEscapeKey(e: KeyboardEvent, onEscape: () => void): boolean {
  if (e.key === 'Escape') {
    e.preventDefault();
    onEscape();
    return true;
  }
  return false;
}

/**
 * Manage modal visibility with proper focus handling
 */
export function manageModalFocus(
  modal: HTMLElement,
  options: {
    onOpen?: () => void;
    onClose?: () => void;
    trapFocus?: boolean;
  } = {}
): {
  show: () => void;
  hide: () => void;
} {
  const trapFocus = options.trapFocus !== false;
  let focusTrapInstance: ReturnType<typeof createFocusTrap> | null = null;
  let previousFocus: HTMLElement | null = null;

  const escapeHandler = (e: Event) => {
    const ke = e as KeyboardEvent;
    handleEscapeKey(ke, hide);
  };

  const show = () => {
    previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    // Show modal
    modal.classList.remove('hidden');
    modal.style.display = '';
    document.body.style.overflow = 'hidden';

    // Handle focus trap
    if (trapFocus) {
      focusTrapInstance = createFocusTrap(modal);
      focusTrapInstance.activate();
    } else {
      // Just move focus to first element
      const firstFocusable = getFocusableElements(modal)[0];
      if (firstFocusable) {
        firstFocusable.focus();
      }
    }

    // Add escape key handler
    document.addEventListener('keydown', escapeHandler);

    // Announce to screen readers
    const titleElement = modal.querySelector('h2, h1, [role="heading"]');
    if (titleElement?.textContent) {
      const message = `${titleElement.textContent} dialog opened`;
      announceToScreenReader(message, 'assertive');
    }

    options.onOpen?.();
  };

  const hide = () => {
    // Hide modal
    modal.classList.add('hidden');
    modal.style.display = 'none';
    document.body.style.overflow = '';

    // Remove focus trap
    if (focusTrapInstance) {
      focusTrapInstance.deactivate();
      focusTrapInstance = null;
    }

    // Remove escape key handler
    document.removeEventListener('keydown', escapeHandler);

    // Restore focus
    if (previousFocus && previousFocus.isConnected) {
      previousFocus.focus();
    }

    options.onClose?.();
  };

  return { show, hide };
}

/**
 * Announce message to screen readers
 */
function announceToScreenReader(
  message: string,
  politeness: 'polite' | 'assertive' = 'polite'
): void {
  const id = `sr-announcer-${politeness}`;
  let announcer = document.getElementById(id);

  if (!announcer) {
    announcer = document.createElement('div');
    announcer.id = id;
    announcer.className = 'sr-only';
    announcer.setAttribute('role', politeness === 'assertive' ? 'alert' : 'status');
    announcer.setAttribute('aria-live', politeness);
    announcer.setAttribute('aria-atomic', 'true');
    document.body.appendChild(announcer);
  }

  // Clear and reset to ensure announcement
  announcer.textContent = '';
  requestAnimationFrame(() => {
    announcer.textContent = message;
  });
}

/**
 * Remove all excessive tabindex attributes (only allow -1 and 0)
 * This ensures semantic HTML and proper tab order
 */
export function cleanupTabindex(container: HTMLElement): void {
  const elementsWithTabindex = container.querySelectorAll('[tabindex]');

  elementsWithTabindex.forEach((el) => {
    const tabindex = el.getAttribute('tabindex');
    if (tabindex === null) return;

    const value = parseInt(tabindex, 10);

    // Only allow tabindex="-1" (not focusable) or tabindex="0" (in tab order)
    // Remove tabindex > 0 as it breaks logical tab order
    if (value > 0) {
      el.removeAttribute('tabindex');
    }
  });
}

/**
 * Ensure semantic HTML for interactive elements
 * Converts role="button" on non-button elements to proper buttons if possible
 */
export function fixSemanticHTML(container: HTMLElement): void {
  // Fix role="button" on list items - these should be buttons
  const buttonLikes = container.querySelectorAll('[role="button"]');

  buttonLikes.forEach((el) => {
    const htmlEl = el as HTMLElement;
    // Ensure elements with role="button" are keyboard accessible
    if (!htmlEl.hasAttribute('tabindex') && htmlEl.tagName !== 'BUTTON') {
      htmlEl.setAttribute('tabindex', '0');
    }

    // Add keyboard handlers if not already present
    const htmlElTyped = htmlEl as HTMLElement & { __keyboardHandlerAdded?: boolean };
    if (!htmlElTyped.__keyboardHandlerAdded) {
      htmlEl.addEventListener('keydown', (e: Event) => {
        const ke = e as KeyboardEvent;
        if (ke.key === 'Enter' || ke.key === ' ') {
          ke.preventDefault();
          htmlEl.click();
        }
      });
      htmlElTyped.__keyboardHandlerAdded = true;
    }
  });
}

/**
 * Sync roving tabindex in a list of elements
 * Only one element should have tabindex="0", others should have tabindex="-1"
 */
export function syncRovingTabindex(container: HTMLElement, currentlyFocused: HTMLElement): void {
  const items = container.querySelectorAll('[role="button"], button, a, li');

  items.forEach((item) => {
    if (item === currentlyFocused) {
      item.setAttribute('tabindex', '0');
    } else {
      item.setAttribute('tabindex', '-1');
    }
  });
}
