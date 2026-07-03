/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Simple typeahead buffer for first-character navigation.
 *
 * Supports:
 * - Prefix matching (buffer accumulates quickly typed keys)
 * - Cycling when repeatedly pressing the same single character
 * - IME composition end (use pushText with composed string)
 */

export type Typeahead = {
  pushKey: (key: string) => string;
  pushText: (text: string) => string;
  reset: () => void;
  getQuery: () => string;
};

function normalizeQuery(value: string): string {
  return value.trim().toLocaleLowerCase();
}

export function createTypeahead(timeoutMs: number = 700): Typeahead {
  let buffer = '';
  let lastTs = 0;

  const reset = (): void => {
    buffer = '';
    lastTs = 0;
  };

  const pushKey = (key: string): string => {
    const now = Date.now();
    const normalized = normalizeQuery(key);
    if (!normalized) {
      return buffer;
    }

    if (lastTs && now - lastTs > timeoutMs) {
      buffer = normalized;
      lastTs = now;
      return buffer;
    }

    // Allow cycling with repeated single-letter presses.
    if (buffer.length === 1 && normalized === buffer) {
      lastTs = now;
      return buffer;
    }

    buffer = normalizeQuery(buffer + normalized);
    lastTs = now;
    return buffer;
  };

  const pushText = (text: string): string => {
    const normalized = normalizeQuery(text);
    if (!normalized) {
      return buffer;
    }
    buffer = normalized;
    lastTs = Date.now();
    return buffer;
  };

  const getQuery = (): string => buffer;

  return { pushKey, pushText, reset, getQuery };
}
