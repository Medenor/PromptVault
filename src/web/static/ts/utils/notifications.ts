/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Notification and status message utilities
 */

import type { TranslationKey } from '@/types/i18n';
import { t } from '@/utils/i18n';

export type NotificationType = 'info' | 'success' | 'warning' | 'error';

/**
 * Show a toast notification
 */
export function showNotification(
  message: string,
  type: NotificationType = 'info',
  duration: number = 5000
): void {
  const notification = document.createElement('div');
  const classType = type === 'warning' ? 'info' : type;

  notification.className = `notification notification-${classType}`;
  notification.textContent = message;
  notification.setAttribute('role', 'alert');
  notification.setAttribute('aria-live', 'polite');

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, duration);
}

/**
 * Show a status message in a specific element
 */
export function showStatus(
  elementId: string,
  message: string,
  type: NotificationType = 'info'
): void {
  const element = document.getElementById(elementId);
  if (element) {
    const classType = type === 'warning' ? 'info' : type;
    element.textContent = message;
    element.className = `status-message status-${classType}`;
    element.classList.remove('hidden');
  }
}

/**
 * Hide a status message element
 */
export function hideStatus(elementId: string): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.classList.add('hidden');
  }
}

/**
 * Show loading indicator
 */
export function showLoading(elementId: string, message?: string): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = message || t('messages.loading');
    element.classList.remove('hidden');
  }
}

/**
 * Confirm dialog wrapper with translation support
 */
export function confirmAction(
  messageKey: TranslationKey,
  options?: Record<string, unknown>
): boolean {
  const message = options ? t(messageKey, options) : t(messageKey);
  return window.confirm(message);
}

/**
 * Report error to telemetry
 */
export function reportError(
  component: string,
  action: string,
  error: unknown,
  metadata?: Record<string, unknown>
): void {
  console.error(`[${component}] ${action}:`, error, metadata);
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(component, action, error, metadata, 'error');
  }
}

/**
 * Report warning to telemetry
 */
export function reportWarning(
  component: string,
  action: string,
  message: string,
  metadata?: Record<string, unknown>
): void {
  console.warn(`[${component}] ${action}:`, message, metadata);
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(component, action, new Error(message), metadata, 'warning');
  }
}
