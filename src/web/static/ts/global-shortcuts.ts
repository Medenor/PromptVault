/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Global keyboard shortcuts shared across all pages.
 *
 * Today, this mainly powers the `?` help modal. Page-specific scripts can
 * listen for `promptvault:open-keyboard-help` and call `detail.markHandled()`
 * to suppress the fallback modal.
 */

import { createModal } from '@components';

type KeyboardHelpEventDetail = {
  markHandled: () => void;
};

let fallbackHelpModal: ReturnType<typeof createModal> | null = null;

function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  return !!el &&
    (el.tagName === 'INPUT' ||
      el.tagName === 'TEXTAREA' ||
      el.tagName === 'SELECT' ||
      el.isContentEditable);
}

function isQuestionShortcut(event: KeyboardEvent): boolean {
  if (event.ctrlKey || event.metaKey) {
    return false;
  }

  // Prefer `event.key === '?'` when available. The extra `code` checks help
  // across keyboard layouts where the generated key can differ.
  return (
    event.key === '?' ||
    (event.shiftKey &&
      (event.code === 'Slash' ||
        event.code === 'NumpadDivide' ||
        event.code === 'Comma' ||
        event.code === 'Digit6'))
  );
}

function openFallbackKeyboardHelpModal(): void {
  if (!fallbackHelpModal) {
    const content = document.createElement('div');
    content.className = 'space-y-3 text-sm text-gray-700';
    content.innerHTML = `
      <p class="text-gray-600">Keyboard shortcuts help:</p>
      <ul class="list-disc list-inside space-y-1">
        <li><strong>?</strong>: Open this help modal</li>
        <li><strong>Escape</strong>: Close dialogs (when supported)</li>
      </ul>
      <div class="pt-2 border-t border-gray-200">
        <p class="text-gray-600">Note:</p>
        <p class="text-gray-600">Some shortcuts are only available on the main prompts page.</p>
      </div>
    `;

    fallbackHelpModal = createModal({
      id: 'keyboard-shortcuts-help-modal-fallback',
      title: 'Keyboard Shortcuts',
      content,
      ariaLabel: 'Keyboard shortcuts help',
      size: 'md',
      actions: [
        {
          label: 'Close',
          variant: 'primary',
          onClick: () => {
            fallbackHelpModal?.close();
          },
        },
      ],
      closeOnEscape: true,
      closeOnBackdrop: true,
      showClose: true,
    });

    document.body.appendChild(fallbackHelpModal.element);
  }

  fallbackHelpModal.open();
}

document.addEventListener('keydown', (event: KeyboardEvent) => {
  if (!isQuestionShortcut(event)) {
    return;
  }

  if (isTypingTarget(event.target)) {
    return;
  }

  event.preventDefault();

  let handled = false;
  const detail: KeyboardHelpEventDetail = {
    markHandled: () => {
      handled = true;
    },
  };

  document.dispatchEvent(new CustomEvent<KeyboardHelpEventDetail>('promptvault:open-keyboard-help', { detail }));

  if (!handled) {
    openFallbackKeyboardHelpModal();
  }
});

