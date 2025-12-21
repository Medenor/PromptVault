/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Frontend telemetry and error reporting
 */

import type { FrontendLogEntry } from '@/types';

const TELEMETRY_ENDPOINT = '/api/logs/frontend';
const MAX_QUEUE_LENGTH = 20;
const OPT_OUT_KEY = 'promptvault.telemetry.optOut';
const pending: FrontendLogEntry[] = [];

function isTelemetryEnabled(): boolean {
  try {
    return localStorage.getItem(OPT_OUT_KEY) !== 'true';
  } catch {
    return true;
  }
}

function setTelemetryEnabled(enabled: boolean): void {
  try {
    if (enabled) {
      localStorage.removeItem(OPT_OUT_KEY);
    } else {
      localStorage.setItem(OPT_OUT_KEY, 'true');
    }
  } catch {
    // Ignore storage failures
  }
}

function serializeError(error: unknown): { message: string; stack?: string | null } {
  if (!error) {
    return { message: 'Unknown error' };
  }
  if (error instanceof Error) {
    return {
      message: error.message || 'Error',
      stack: error.stack || null,
    };
  }
  if (typeof error === 'string') {
    return { message: error };
  }
  try {
    return { message: JSON.stringify(error).slice(0, 500) };
  } catch {
    return { message: String(error) };
  }
}

function sendPayload(entry: FrontendLogEntry): void {
  const body = JSON.stringify(entry);

  if (navigator.sendBeacon) {
    try {
      const blob = new Blob([body], { type: 'application/json' });
      if (navigator.sendBeacon(TELEMETRY_ENDPOINT, blob)) {
        return;
      }
    } catch {
      // Fallback to fetch below
    }
  }

  fetch(TELEMETRY_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    credentials: 'same-origin',
    keepalive: true,
  }).catch(() => {
    // Ignore network failures
  });
}

function reportError(
  component: string,
  action: string,
  error: unknown,
  metadata: Record<string, unknown> = {},
  severity: 'error' | 'warning' | 'info' = 'error'
): void {
  if (!isTelemetryEnabled()) {
    return;
  }
  if (pending.length >= MAX_QUEUE_LENGTH) {
    pending.shift();
  }

  const details = serializeError(error);
  const payload: FrontendLogEntry = {
    component: component || 'unknown',
    action: action || 'runtime.error',
    message: details.message,
    severity: severity || 'error',
    url: window.location.href,
    context: metadata,
    ...(details.stack ? { stack: details.stack } : {}),
  };

  pending.push(payload);
  sendPayload(payload);
}

window.FrontendLogger = {
  reportError,
  enable: () => {
    setTelemetryEnabled(true);
  },
  disable: () => {
    setTelemetryEnabled(false);
  },
  isEnabled: isTelemetryEnabled,
};

window.addEventListener('error', (event) => {
  if (!event) {
    return;
  }
  const metadata = {
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
  };
  reportError('window', 'error', event.error || event.message, metadata);
});

window.addEventListener('unhandledrejection', (event) => {
  if (!event) {
    return;
  }
  const reason = event.reason || {};
  reportError('window', 'unhandledrejection', reason, {});
});

export { reportError };
