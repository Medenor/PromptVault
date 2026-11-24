/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const WEB = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..'); // src/web

const template = readFileSync(path.join(WEB, 'templates', 'import_export.html'), 'utf-8');
const source = readFileSync(path.join(WEB, 'static', 'ts', 'import-export.ts'), 'utf-8');
const clearFn = source.slice(source.indexOf('function clearExportSettings'));

describe('export panel "Clear" restores the template defaults', () => {
  it('unchecks the favorites-only box (template default is unchecked)', () => {
    expect(template).not.toMatch(/id="include-favorites"[^>]*\schecked/);
    expect(clearFn).toContain('includeFavorites.checked = false');
  });

  it('resets the filename to the template default', () => {
    const match = /id="export-filename"[^>]*value="([^"]*)"/s.exec(template);
    expect(match?.[1]).toBe('promptvault_export');
    expect(clearFn).toContain("filenameInput.value = 'promptvault_export'");
  });

  it('uses well-formed headings in the cards', () => {
    expect(template).not.toMatch(/<h2[^>]*>[^<]*<\/h3>/);
  });
});
