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
import { t } from '@/utils/i18n';
import { initButtonKeyboardActivation } from '@/utils/button-keyboard-activation';
import { html } from '@/utils/safe-html';

type KeyboardHelpEventDetail = {
  markHandled: () => void;
};

let fallbackHelpModal: ReturnType<typeof createModal> | null = null;

function ensureKeyboardNavigationAnnouncer(): void {
  if (document.getElementById('keyboard-navigation-announcer')) {
    return;
  }
  const el = document.createElement('div');
  el.id = 'keyboard-navigation-announcer';
  el.className = 'sr-only';
  el.setAttribute('aria-live', 'polite');
  document.body.insertBefore(el, document.body.firstChild);
}

function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  return (
    !!el &&
    (el.tagName === 'INPUT' ||
      el.tagName === 'TEXTAREA' ||
      el.tagName === 'SELECT' ||
      el.isContentEditable)
  );
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
    // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
    content.innerHTML = html`
      <p class="text-gray-600">${t('accessibility.keyboardHelp.shortcutsHeading')}</p>
      <ul class="list-disc list-inside space-y-1">
        <li><strong>?</strong>: ${t('accessibility.keyboardHelp.shortcutQuestion')}</li>
        <li><strong>Escape</strong>: ${t('accessibility.keyboardHelp.shortcutEscape')}</li>
      </ul>
      <div class="pt-2 border-t border-gray-200">
        <p class="text-gray-600">${t('accessibility.keyboardHelp.fallbackNoteHeading')}</p>
        <p class="text-gray-600">${t('accessibility.keyboardHelp.fallbackNoteBody')}</p>
      </div>
    `;

    fallbackHelpModal = createModal({
      id: 'keyboard-shortcuts-help-modal-fallback',
      title: t('accessibility.keyboardHelp.title'),
      content,
      ariaLabel: t('accessibility.keyboardHelp.ariaLabel'),
      size: 'md',
      actions: [
        {
          label: t('actions.close'),
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
  if (document.readyState !== 'loading') {
    ensureKeyboardNavigationAnnouncer();
  }
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

  document.dispatchEvent(
    new CustomEvent<KeyboardHelpEventDetail>('promptvault:open-keyboard-help', { detail })
  );

  if (!handled) {
    openFallbackKeyboardHelpModal();
  }
});

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    ensureKeyboardNavigationAnnouncer();
    initButtonKeyboardActivation();
  });
} else {
  ensureKeyboardNavigationAnnouncer();
  initButtonKeyboardActivation();
}
