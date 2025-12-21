/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Notification and status message utilities
 */

import i18next from 'i18next';

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
    element.classList.remove('is-hidden');
  }
}

/**
 * Hide a status message element
 */
export function hideStatus(elementId: string): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.classList.add('is-hidden');
  }
}

/**
 * Show loading indicator
 */
export function showLoading(elementId: string, message?: string): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = message || i18next.t('common.loading');
    element.classList.remove('is-hidden');
  }
}

/**
 * Confirm dialog wrapper with translation support
 */
export function confirmAction(messageKey: string, options?: Record<string, unknown>): boolean {
  const message = i18next.t(messageKey, options);
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
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(component, action, error, metadata, 'error');
  }
  console.error(`[${component}] ${action}:`, error);
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
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(component, action, new Error(message), metadata, 'warning');
  }
  console.warn(`[${component}] ${action}:`, message);
}
