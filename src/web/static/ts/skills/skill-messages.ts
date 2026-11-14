/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Translated, user-facing text for skill errors, warnings and sizes.
 *
 * All values returned here are plain text: callers must put them in the DOM
 * with textContent (archive entry names and server messages are untrusted).
 */

import { t, tUnsafe } from '@/utils/i18n';
import type { SkillApiError } from './skill-api';

const UNITS = ['B', 'KB', 'MB', 'GB'] as const;

/** Human-readable size, e.g. 1536 -> "1.5 KB". */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '0 B';
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const rounded = unit === 0 || value >= 10 ? Math.round(value) : Math.round(value * 10) / 10;
  return `${rounded} ${UNITS[unit]}`;
}

/** Translated message for an API error code; falls back to the generic text. */
export function describeSkillError(error: SkillApiError): {
  message: string;
  entry: string | null;
} {
  const key = `skills.errors.${error.code}`;
  const translated = tUnsafe(key);
  const message = translated === key ? t('skills.errors.unknown') : translated;
  const entry =
    error.offendingEntry === null
      ? null
      : tUnsafe('skills.import.offendingEntry', {
          entry: error.offendingEntry,
          interpolation: { escapeValue: false },
        });
  return { message, entry };
}

/** Translated lines for format warning codes; unknown codes are shown as-is. */
export function describeWarnings(codes: readonly string[]): string[] {
  return codes.map((code) => {
    const key = `skills.warnings.${code}`;
    const translated = tUnsafe(key);
    return translated === key ? code : translated;
  });
}
