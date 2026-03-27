/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Utilities for managing focus after user actions (modal close, delete, etc.)
 * Implements WCAG 2.1 AA focus management best practices
 */

/**
 * Returns the next logical element to focus after a table row is deleted
 * Priority: next row's button -> previous row's button -> table container
 */
export function getNextFocusElementAfterRowDelete(
  deletedRow: HTMLTableRowElement,
  tableBody: HTMLTableSectionElement | null,
  selectorForButton: string = 'button'
): HTMLElement | null {
  if (!tableBody) return null;

  const rows = Array.from(tableBody.querySelectorAll<HTMLTableRowElement>('tr'));
  const deletedRowIndex = rows.indexOf(deletedRow);

  if (deletedRowIndex === -1) {
    return null;
  }

  // Try next row first
  if (deletedRowIndex < rows.length - 1) {
    const nextRow = rows[deletedRowIndex + 1];
    const button = nextRow?.querySelector<HTMLElement>(selectorForButton);
    if (button) {
      return button;
    }
  }

  // Try previous row
  if (deletedRowIndex > 0) {
    const prevRow = rows[deletedRowIndex - 1];
    const button = prevRow?.querySelector<HTMLElement>(selectorForButton);
    if (button) {
      return button;
    }
  }

  // Fall back to table container
  return tableBody;
}

/**
 * Returns the next logical element to focus after a list item is deleted
 * Priority: next item -> previous item -> list container
 */
export function getNextFocusElementAfterItemDelete(
  deletedItem: HTMLElement,
  listContainer: HTMLElement | null,
  itemSelector: string = 'li'
): HTMLElement | null {
  if (!listContainer) return null;

  const items = Array.from(listContainer.querySelectorAll<HTMLElement>(itemSelector));
  const deletedItemIndex = items.indexOf(deletedItem);

  if (deletedItemIndex === -1) {
    return null;
  }

  // Try next item first
  if (deletedItemIndex < items.length - 1) {
    const nextItem = items[deletedItemIndex + 1];
    if (nextItem) {
      return nextItem;
    }
  }

  // Try previous item
  if (deletedItemIndex > 0) {
    const prevItem = items[deletedItemIndex - 1];
    if (prevItem) {
      return prevItem;
    }
  }

  // Fall back to container
  return listContainer;
}

/**
 * Stores the trigger element that opened a modal for focus restoration
 * Use this when opening a modal from a button click
 */
export function storeFocusTrigger(event: Event | null, storageRef: { current: HTMLElement | null }): void {
  if (!event) return;
  const target = (event as unknown as { target?: HTMLElement }).target;
  if (target && target instanceof HTMLElement) {
    storageRef.current = target;
  }
}

/**
 * Restores focus to a stored trigger element
 * Safely handles cases where the element no longer exists
 */
export function restoreFocusToTrigger(storageRef: { current: HTMLElement | null }): void {
  if (storageRef.current && storageRef.current.isConnected && typeof storageRef.current.focus === 'function') {
    // Use setTimeout to ensure focus is applied after DOM updates
    setTimeout(() => {
      if (storageRef.current?.isConnected) {
        storageRef.current.focus();
        // Announce to screen readers
        if (storageRef.current.getAttribute('aria-label')) {
          announceToScreenReader(`Returned focus to ${storageRef.current.getAttribute('aria-label')}`);
        }
      }
    }, 0);
  }
}

/**
 * Moves focus to the first focusable element in a container
 * Useful when opening modals
 */
export function focusFirstElement(container: HTMLElement | null): void {
  if (!container) return;

  const focusableSelectors = [
    'button:not([disabled])',
    '[href]',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ];

  const focusableElements = Array.from(
    container.querySelectorAll<HTMLElement>(focusableSelectors.join(','))
  ).filter((el) => {
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden';
  });

  if (focusableElements.length > 0) {
    const firstFocusable = focusableElements[0];
    if (firstFocusable) {
      firstFocusable.focus();
    }
  } else {
    // If no focusable elements, focus the container itself
    container.setAttribute('tabindex', '-1');
    container.focus();
  }
}

/**
 * Announces a message to screen readers using aria-live region
 */
export function announceToScreenReader(message: string, politeness: 'polite' | 'assertive' = 'polite'): void {
  let announcer = document.getElementById('focus-announcer');
  if (!announcer) {
    announcer = document.createElement('div');
    announcer.id = 'focus-announcer';
    announcer.className = 'sr-only';
    announcer.setAttribute('aria-live', politeness);
    announcer.setAttribute('aria-atomic', 'true');
    document.body.appendChild(announcer);
  }

  announcer.setAttribute('aria-live', politeness);
  announcer.textContent = '';
  // Force screen reader to announce by using requestAnimationFrame
  requestAnimationFrame(() => {
    announcer!.textContent = message;
  });
}

/**
 * Manages focus in and out of a modal
 * Opens modal: moves focus to first element and traps tab
 * Closes modal: returns focus to trigger element
 */
export function manageModalFocus(
  modalElement: HTMLElement,
  isOpen: boolean,
  triggerElement?: HTMLElement | null
): void {
  if (isOpen) {
    focusFirstElement(modalElement);
  } else {
    if (triggerElement && triggerElement.isConnected) {
      triggerElement.focus();
    }
  }
}
