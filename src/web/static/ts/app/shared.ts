/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { t } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';

export const HIDDEN_CLASS = 'hidden';
export const ERROR_VISIBLE_CLASS = 'validation-error-visible';
export const APP_COMPONENT = 'app';
export const MAX_TAGS = 15;

export function reportAppIssue(
  action: string,
  error: unknown,
  metadata: Record<string, unknown> = {},
  severity: 'error' | 'warning' = 'error'
): void {
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(APP_COMPONENT, action, error, metadata, severity);
  }
  const message = `[PromptVault][app] ${action}`;
  if (severity === 'warning') {
    console.warn(message, error, metadata);
  } else {
    console.error(message, error, metadata);
  }
}

export function showElement(element: HTMLElement | null): void {
  if (element) {
    element.classList.remove(HIDDEN_CLASS);
  }
}

export function hideElement(element: HTMLElement | null): void {
  if (element) {
    element.classList.add(HIDDEN_CLASS);
  }
}

export function toggleElement(element: HTMLElement | null, shouldShow: boolean): void {
  if (element) {
    element.classList.toggle(HIDDEN_CLASS, !shouldShow);
  }
}

export function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (m) => map[m] ?? m);
}

// Offline mode is read/copy-only (FR-009) — writes (create/edit/delete/revert/
// bulk actions) require connectivity rather than being queued for later sync.
// Returns false (and shows the standard notification) when offline, so callers
// can early-return with `if (!guardOnlineOnly()) return;`.
export function guardOnlineOnly(): boolean {
  if (!navigator.onLine) {
    showNotification(t('offline.editUnavailable'), 'error');
    return false;
  }
  return true;
}
