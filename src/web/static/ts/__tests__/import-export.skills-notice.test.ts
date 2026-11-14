/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..'); // src/web/static
const LANGS = ['en', 'fr', 'es', 'de'] as const;

type Tree = { [key: string]: string | Tree };

function locale(lang: string): Tree {
  return JSON.parse(readFileSync(path.join(ROOT, 'locales', `${lang}.json`), 'utf-8')) as Tree;
}

function leafKeys(tree: Tree, prefix = ''): string[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === 'string' ? [`${prefix}${key}`] : leafKeys(value, `${prefix}${key}.`)
  );
}

function section(lang: string, name: string): Tree {
  return locale(lang)[name] as Tree;
}

describe('skills notice on the import/export page', () => {
  it('is rendered by the template with its translation key', () => {
    const template = readFileSync(
      path.join(ROOT, '..', 'templates', 'import_export.html'),
      'utf-8'
    );
    expect(template).toContain('id="skills-excluded-notice"');
    expect(template).toContain('data-i18n="importExport.skillsExcluded"');
    expect(template).toContain('data-i18n="importExport.skillsExcludedTitle"');
  });

  it.each(LANGS)('has a translated notice in %s', (lang) => {
    const strings = section(lang, 'importExport') as Record<string, string>;
    for (const key of ['skillsExcluded', 'skillsExcludedTitle'] as const) {
      expect(typeof strings[key]).toBe('string');
      expect(strings[key]?.length).toBeGreaterThan(10);
    }
  });
});

describe('skills locale completeness', () => {
  const enKeys = leafKeys(section('en', 'skills')).sort();

  it('defines every warning and error code the API can return', () => {
    const warnings = Object.keys(section('en', 'skills')['warnings'] as Tree).sort();
    expect(warnings).toEqual(
      [
        'frontmatter_missing',
        'frontmatter_malformed',
        'name_missing',
        'name_invalid',
        'name_folder_mismatch',
        'description_missing',
        'description_too_long',
        'no_wrapping_folder',
        'skill_md_not_utf8',
      ].sort()
    );
    const errors = Object.keys(section('en', 'skills')['errors'] as Tree);
    for (const code of [
      'ARCHIVE_INVALID',
      'ARCHIVE_ENCRYPTED',
      'SKILL_MD_MISSING',
      'ENTRY_PATH_UNSAFE',
      'ENTRY_LINK',
      'ENTRY_NAME_INVALID',
      'ENTRY_DUPLICATE',
      'LIMIT_DEPTH',
      'LIMIT_FILE_COUNT',
      'LIMIT_FILE_SIZE',
      'LIMIT_TOTAL_SIZE',
      'ARCHIVE_SUSPICIOUS_RATIO',
      'LIMIT_SKILL_MD_SIZE',
      'LIMIT_UPLOAD_SIZE',
      'SKILL_NOT_FOUND',
      'FILE_NOT_FOUND',
      'ITEM_IS_SKILL',
      'ITEM_IS_PROMPT',
      'unknown',
    ]) {
      expect(errors, code).toContain(code);
    }
  });

  it.each(LANGS.filter((lang) => lang !== 'en'))('%s has exactly the keys English has', (lang) => {
    expect(leafKeys(section(lang, 'skills')).sort()).toEqual(enKeys);
  });

  it.each(LANGS)('%s has no empty skill strings', (lang) => {
    const strings = leafKeys(section(lang, 'skills')).map((key) =>
      key
        .split('.')
        .reduce<
          Tree | string
        >((node, part) => (node as Tree)[part] as Tree | string, section(lang, 'skills'))
    );
    expect(strings.every((value) => typeof value === 'string' && value.trim() !== '')).toBe(true);
  });

  it.each(LANGS)('%s translates the type filter and import entry point', (lang) => {
    expect(leafKeys(section(lang, 'filters')).sort()).toEqual(
      ['itemType.all', 'itemType.label', 'itemType.prompt', 'itemType.skill'].sort()
    );
    expect(typeof (section(lang, 'nav') as Record<string, string>)['importSkill']).toBe('string');
    expect(typeof ((section(lang, 'search')['filter'] as Tree)['type'] as string)).toBe('string');
  });
});
