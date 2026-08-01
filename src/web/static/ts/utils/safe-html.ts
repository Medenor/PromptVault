/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Structural HTML escaping for template literals.
 *
 * Use the `html` tagged template to build innerHTML strings: every
 * interpolated value is escaped by default, so a missed escapeHtml() call
 * can no longer slip through. Wrap pre-built, trusted HTML fragments
 * (e.g. the output of a nested `html` call) in `raw()` to opt out.
 */

import { escapeHtml } from './dom';

export interface RawHtml {
  readonly __raw: true;
  readonly value: string;
}

export function raw(value: string): RawHtml {
  return { __raw: true, value };
}

function isRawHtml(value: unknown): value is RawHtml {
  return typeof value === 'object' && value !== null && (value as RawHtml).__raw === true;
}

function escapeValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }
  if (isRawHtml(value)) {
    return value.value;
  }
  if (Array.isArray(value)) {
    return value.map((item) => escapeValue(item)).join('');
  }
  return escapeHtml(String(value));
}

export function html(strings: TemplateStringsArray, ...values: unknown[]): string {
  let result = strings[0] ?? '';
  for (let i = 0; i < values.length; i++) {
    result += escapeValue(values[i]);
    result += strings[i + 1] ?? '';
  }
  return result;
}
