/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { ModalProps } from './types';
import { createButton } from './button';

/**
 * Creates a modal dialog with overlay
 * @param props - Modal properties (title, content, actions, size, etc.)
 * @returns Object with modal element and open/close methods
 */
export function createModal(props: ModalProps): {
  element: HTMLDivElement;
  open: () => void;
  close: () => void;
} {
  // Overlay (backdrop)
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black/50 hidden';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  const dialogId = props.id || `pv-modal-${Math.random().toString(36).slice(2, 10)}`;
  modal.id = dialogId;
  if (props.ariaLabel) {
    modal.setAttribute('aria-label', props.ariaLabel);
  }

  // Modal card container
  const modalContent = document.createElement('div');
  const baseClasses = 'bg-white rounded-lg shadow-lg relative';
  const sizeClasses = getSizeClasses(props.size || 'md');
  const paddingClasses = 'p-6';

  modalContent.className =
    `${baseClasses} ${sizeClasses} ${paddingClasses} ${props.className || ''}`.trim();

  // Header with title and close button
  const titleId = `${dialogId}-title`;
  const descriptionId = `${dialogId}-description`;

  if (props.title) {
    const header = document.createElement('div');
    header.className = 'flex items-center justify-between mb-4';

    const title = document.createElement('h2');
    title.id = titleId;
    title.textContent = props.title;
    title.className = 'text-xl font-bold text-gray-900';
    header.appendChild(title);
    if (!props.ariaLabel) {
      modal.setAttribute('aria-labelledby', titleId);
    }

    // Close button (X) in top-right
    if (props.showClose !== false && (props.closable === undefined || props.closable)) {
      const closeBtn = document.createElement('button');
      closeBtn.innerHTML = '&times;';
      closeBtn.className =
        'text-gray-400 hover:text-gray-600 text-3xl leading-none transition-colors duration-200';
      closeBtn.setAttribute('aria-label', 'Close modal');
      closeBtn.addEventListener('click', () => {
        close();
      });
      header.appendChild(closeBtn);
    }

    modalContent.appendChild(header);
  }

  // Body content
  const body = document.createElement('div');
  body.id = descriptionId;
  body.className = 'mb-6';
  if (typeof props.content === 'string') {
    body.innerHTML = props.content;
  } else {
    body.appendChild(props.content);
  }
  modalContent.appendChild(body);
  modal.setAttribute('aria-describedby', descriptionId);

  // Actions footer (buttons)
  if (props.actions && props.actions.length > 0) {
    const footer = document.createElement('div');
    footer.className = 'flex justify-end gap-2';

    props.actions.forEach((action) => {
      const button = createButton(action.label, {
        variant: action.variant || 'secondary',
        onClick: () => {
          action.onClick();
        },
      });
      footer.appendChild(button);
    });

    modalContent.appendChild(footer);
  }

  modal.appendChild(modalContent);

  // Close on backdrop click
  if (props.closeOnBackdrop !== false) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        close();
      }
    });
  }

  // Close on ESC key
  const escapeHandler = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
      if (props.closeOnEscape !== false) {
        close();
      }
    }
  };

  // Focus trap state
  const focusableElements =
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
  let firstFocusable: HTMLElement | null = null;
  let lastFocusable: HTMLElement | null = null;
  let previouslyFocused: HTMLElement | null = null;

  const open = () => {
    previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', escapeHandler);

    // Set up focus trap
    const focusables = modalContent.querySelectorAll<HTMLElement>(focusableElements);
    if (focusables.length > 0) {
      firstFocusable = focusables[0] || null;
      lastFocusable = focusables[focusables.length - 1] || null;
      if (firstFocusable) {
        firstFocusable.focus();
      }
    } else {
      modalContent.setAttribute('tabindex', '-1');
      modalContent.focus();
    }

    // Trap focus within modal
    document.addEventListener('keydown', trapFocus);
  };

  const close = () => {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
    document.removeEventListener('keydown', escapeHandler);
    document.removeEventListener('keydown', trapFocus);
    if (previouslyFocused) {
      previouslyFocused.focus();
    }
    if (props.onClose) {
      props.onClose();
    }
  };

  const trapFocus = (e: KeyboardEvent) => {
    if (e.key !== 'Tab') return;

    if (e.shiftKey) {
      // Shift + Tab
      if (document.activeElement === firstFocusable && lastFocusable) {
        e.preventDefault();
        lastFocusable.focus();
      }
    } else {
      // Tab
      if (document.activeElement === lastFocusable && firstFocusable) {
        e.preventDefault();
        firstFocusable.focus();
      }
    }
  };

  return {
    element: modal,
    open,
    close,
  };
}

/**
 * Creates a confirmation modal with OK/Cancel buttons
 * @param message - Confirmation message
 * @param onConfirm - Callback when user confirms
 * @param onCancel - Optional callback when user cancels
 * @returns Modal object
 */
export function createConfirmModal(
  message: string,
  onConfirm: () => void,
  onCancel?: () => void
): {
  element: HTMLDivElement;
  open: () => void;
  close: () => void;
} {
  const modal = createModal({
    title: 'Confirm',
    content: message,
    size: 'sm',
    actions: [
      {
        label: 'Cancel',
        variant: 'secondary',
        onClick: () => {
          modal.close();
          if (onCancel) onCancel();
        },
      },
      {
        label: 'Confirm',
        variant: 'primary',
        onClick: () => {
          modal.close();
          onConfirm();
        },
      },
    ],
  });

  return modal;
}

/**
 * Creates an alert modal with single OK button
 * @param message - Alert message
 * @param onClose - Optional callback when closed
 * @returns Modal object
 */
export function createAlertModal(
  message: string,
  onClose?: () => void
): {
  element: HTMLDivElement;
  open: () => void;
  close: () => void;
} {
  const modal = createModal({
    title: 'Alert',
    content: message,
    size: 'sm',
    actions: [
      {
        label: 'OK',
        variant: 'primary',
        onClick: () => {
          modal.close();
          if (onClose) onClose();
        },
      },
    ],
  });

  return modal;
}

/**
 * Get size classes for modal
 * @param size - Modal size
 * @returns Tailwind classes
 */
function getSizeClasses(size: string): string {
  const sizes: Record<string, string> = {
    sm: 'max-w-sm w-full',
    md: 'max-w-md w-full',
    lg: 'max-w-lg w-full',
    xl: 'max-w-xl w-full',
    '2xl': 'max-w-2xl w-full',
    full: 'max-w-full w-full h-full',
  };
  return sizes[size] || sizes['md'] || '';
}
