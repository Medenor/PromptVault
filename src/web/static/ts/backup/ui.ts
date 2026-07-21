/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { t } from '@/utils/i18n';
import { announce } from '@/utils/a11y';
import type { FormValidationError } from './types';

const liveValidationState = new Map<string, boolean>();

export function resetFieldError(inputId: string, errorId: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId);
  input?.setAttribute('aria-invalid', 'false');
  if (error) {
    error.textContent = '';
  }
}

export function addFieldError(
  errors: FormValidationError[],
  inputId: string,
  errorId: string,
  message: string
): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId);
  if (input) {
    const existing =
      input
        .getAttribute('aria-describedby')
        ?.split(/\s+/)
        .map((s) => s.trim())
        .filter(Boolean) ?? [];
    const next = Array.from(new Set([...existing, errorId]));
    input.setAttribute('aria-describedby', next.join(' '));
  }
  input?.setAttribute('aria-invalid', 'true');
  if (error) {
    error.textContent = message;
  }
  errors.push({ inputId, message });
}

export function setLiveFieldError(inputId: string, errorId: string, message: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;
  input?.setAttribute('aria-invalid', 'true');
  if (error) {
    error.textContent = message;
  }
  liveValidationState.set(inputId, true);
  if (!hadError) {
    announce(message, { id: 'validation-announcer', politeness: 'polite' });
  }
}

export function clearLiveFieldError(inputId: string, errorId: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;
  input?.setAttribute('aria-invalid', 'false');
  if (error) {
    error.textContent = '';
  }
  liveValidationState.set(inputId, false);
  if (hadError) {
    announce(t('validation.fieldValid') || 'Field is valid.', {
      id: 'validation-announcer',
      politeness: 'polite',
    });
  }
}

export function getLiveValidationState(inputId: string): boolean {
  return liveValidationState.get(inputId) === true;
}

export function resetErrorSummary(summaryId: string): void {
  const summary = document.getElementById(summaryId);
  if (!summary) return;
  summary.textContent = '';
  summary.style.display = 'none';
}

export function renderErrorSummary(summaryId: string, errors: FormValidationError[]): void {
  if (errors.length === 0) {
    return;
  }

  const summary = document.getElementById(summaryId);
  if (!summary) {
    const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
    firstInput?.focus();
    return;
  }

  summary.textContent = '';
  const header = document.createElement('p');
  header.className = 'error-banner-header';
  header.textContent = t('validation.errorSummaryHeader') || 'Please correct the following errors:';
  summary.appendChild(header);

  const list = document.createElement('ul');
  list.className = 'error-banner-list';
  errors.forEach((error) => {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = `#${error.inputId}`;
    link.className = 'underline';
    link.textContent = error.message;
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const target = document.getElementById(error.inputId) as HTMLElement | null;
      target?.focus();
    });
    item.appendChild(link);
    list.appendChild(item);
  });
  summary.appendChild(list);
  summary.style.display = 'block';

  // Per plan T-ACC023: focus the first invalid field after rendering the summary.
  const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
  if (firstInput) {
    firstInput.focus();
  } else {
    summary.focus();
  }
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function showProgress(containerId: string, message: string): void {
  const container = document.getElementById(containerId);
  const fill = document.getElementById(`${containerId}-fill`);
  const status = document.getElementById(containerId.replace('-progress', '-status'));

  container?.classList.remove('hidden');
  if (fill instanceof HTMLElement) {
    fill.style.width = '50%';
  }
  if (status) {
    status.textContent = message;
    status.className = 'text-sm text-blue-600 mt-2';
  }
}

export function hideProgress(containerId: string): void {
  const container = document.getElementById(containerId);
  container?.classList.add('hidden');
}

// Set by index.ts to avoid a circular import with the monitoring dashboard wiring.
let refreshMonitoringImpl: () => void = () => {};
export function setRefreshMonitoring(fn: () => void): void {
  refreshMonitoringImpl = fn;
}
export function refreshMonitoring(): void {
  refreshMonitoringImpl();
}

export function showStatus(
  elementId: string,
  message: string,
  type: 'info' | 'success' | 'error'
): void {
  const element = document.getElementById(elementId);
  if (!element) return;

  element.textContent = message;
  const colorClass =
    type === 'success' ? 'text-green-600' : type === 'error' ? 'text-red-600' : 'text-blue-600';
  element.className = `text-sm ${colorClass} mt-2`;

  const container = element.parentElement;
  if (container && container.id.includes('progress')) {
    container.classList.remove('hidden');
  }

  if (type === 'success') {
    setTimeout(() => {
      if (container && container.id.includes('progress')) {
        container.classList.add('hidden');
      }
    }, 5000);
  }
}
