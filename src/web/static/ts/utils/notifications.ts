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

function createNotificationIcon(type: NotificationType): SVGSVGElement {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('width', '18');
  svg.setAttribute('height', '18');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  svg.classList.add('notification-icon');

  const path = document.createElementNS(ns, 'path');
  path.setAttribute('fill', 'currentColor');

  // Keep icons simple and consistent; they are purely decorative for sighted users.
  switch (type) {
    case 'success':
      // Check in a circle
      path.setAttribute(
        'd',
        'M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm-1 14.2-3.2-3.2 1.4-1.4 1.8 1.8 4.6-4.6 1.4 1.4Z'
      );
      break;
    case 'warning':
      // Exclamation triangle
      path.setAttribute(
        'd',
        'M1 21h22L12 2 1 21Zm12-3h-2v-2h2v2Zm0-4h-2v-4h2v4Z'
      );
      break;
    case 'error':
      // X in a circle
      path.setAttribute(
        'd',
        'M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm3.5 13.1-1.4 1.4L12 13.4l-2.1 2.1-1.4-1.4L10.6 12 8.5 9.9l1.4-1.4L12 10.6l2.1-2.1 1.4 1.4L13.4 12Z'
      );
      break;
    case 'info':
    default:
      // i in a circle
      path.setAttribute(
        'd',
        'M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm1 15h-2V11h2v6Zm0-8h-2V7h2v2Z'
      );
      break;
  }

  svg.appendChild(path);
  return svg;
}

/**
 * Show a toast notification
 */
export function showNotification(
  message: string,
  type: NotificationType = 'info',
  duration: number = 5000
): void {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.setAttribute('data-notification-type', type);

  const icon = createNotificationIcon(type);
  const text = document.createElement('span');
  text.className = 'notification-text';
  text.textContent = message;
  notification.append(icon, text);

  // Errors should interrupt; other toasts are informational and should not steal
  // the screen reader cursor or speech queue.
  notification.setAttribute('role', type === 'error' ? 'alert' : 'status');
  notification.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');
  notification.setAttribute('aria-atomic', 'true');

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
    element.textContent = message;
    element.className = `status-message status-${type}`;
    element.setAttribute('role', type === 'error' ? 'alert' : 'status');
    element.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');
    element.setAttribute('aria-atomic', 'true');
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
