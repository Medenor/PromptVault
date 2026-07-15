/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Detects `[NAME]` / `{NAME}` placeholder tokens in prompt content and
 * substitutes user-filled values at copy time. Purely client-side and
 * transient — nothing here is persisted.
 */

export type PlaceholderToken = {
  raw: string;
  delimiter: 'bracket' | 'brace';
  label: string;
};

const BRACKET_RE = /\[([^[\]\n]+)\]/g;
const BRACE_RE = /\{([^{}\n]+)\}/g;

function collectMatches(
  content: string,
  re: RegExp,
  delimiter: 'bracket' | 'brace'
): PlaceholderToken[] {
  const tokens: PlaceholderToken[] = [];
  for (const match of content.matchAll(re)) {
    const label = match[1];
    if (label === undefined) {
      continue;
    }
    tokens.push({ raw: match[0], delimiter, label });
  }
  return tokens;
}

export function detectPlaceholders(content: string): PlaceholderToken[] {
  if (!content) {
    return [];
  }

  const bracketMatches = collectMatches(content, BRACKET_RE, 'bracket').map((token) => ({
    token,
    index: content.indexOf(token.raw),
  }));
  const braceMatches = collectMatches(content, BRACE_RE, 'brace').map((token) => ({
    token,
    index: content.indexOf(token.raw),
  }));

  const seen = new Set<string>();
  const result: PlaceholderToken[] = [];
  for (const { token } of [...bracketMatches, ...braceMatches].sort((a, b) => a.index - b.index)) {
    if (seen.has(token.raw)) {
      continue;
    }
    seen.add(token.raw);
    result.push(token);
  }
  return result;
}

export function substitutePlaceholders(content: string, values: Map<string, string>): string {
  if (values.size === 0) {
    return content;
  }

  const keys = [...values.keys()].sort((a, b) => b.length - a.length);
  const pattern = new RegExp(
    keys.map((key) => key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'),
    'g'
  );

  return content.replace(pattern, (matched) => values.get(matched) ?? matched);
}
