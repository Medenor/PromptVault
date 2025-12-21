/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

(function () {
  const TELEMETRY_ENDPOINT = '/api/logs/frontend';
  const MAX_QUEUE_LENGTH = 20;
  const OPT_OUT_KEY = 'promptvault.telemetry.optOut';
  const pending = [];

  function isTelemetryEnabled() {
    try {
      return localStorage.getItem(OPT_OUT_KEY) !== 'true';
    } catch (_err) {
      return true;
    }
  }

  function setTelemetryEnabled(enabled) {
    try {
      if (enabled) {
        localStorage.removeItem(OPT_OUT_KEY);
      } else {
        localStorage.setItem(OPT_OUT_KEY, 'true');
      }
    } catch (_err) {
      // Ignore storage failures
    }
  }

  function serializeError(error) {
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
    } catch (_err) {
      return { message: String(error) };
    }
  }

  function sendPayload(entry) {
    const body = JSON.stringify(entry);

    if (navigator.sendBeacon) {
      try {
        const blob = new Blob([body], { type: 'application/json' });
        if (navigator.sendBeacon(TELEMETRY_ENDPOINT, blob)) {
          return;
        }
      } catch (_err) {
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

  function reportError(component, action, error, metadata = {}, severity = 'error') {
    if (!isTelemetryEnabled()) {
      return;
    }
    if (pending.length >= MAX_QUEUE_LENGTH) {
      pending.shift();
    }

    const details = serializeError(error);
    const payload = {
      component: component || 'unknown',
      action: action || 'runtime.error',
      message: details.message,
      stack: details.stack,
      severity: severity || 'error',
      url: window.location.href,
      context: metadata,
    };

    pending.push(payload);
    sendPayload(payload);
  }

  window.FrontendLogger = {
    reportError,
    enable: function () {
      setTelemetryEnabled(true);
    },
    disable: function () {
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
})();
