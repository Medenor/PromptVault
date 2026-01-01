/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderCharacterDiff } from '../diff-renderer';
import type { DiffOperation } from '../../types/api/responses';

describe('renderCharacterDiff', () => {
  beforeEach(() => {
    // Clean up DOM before each test
    document.body.innerHTML = '';
  });

  it('should render equal operations with correct styling', () => {
    const operations: DiffOperation[] = [
      { op: 'equal', text: 'Hello world' },
    ];

    const result = renderCharacterDiff(operations);

    expect(result).toBeInstanceOf(HTMLElement);
    expect(result.className).toContain('whitespace-pre-wrap');
    expect(result.className).toContain('break-words');

    const spans = result.querySelectorAll('span');
    expect(spans.length).toBe(1);
    expect(spans[0]?.textContent).toBe('Hello world');
    expect(spans[0]?.className).toBe('text-gray-700');
  });

  it('should render delete operations with correct styling', () => {
    const operations: DiffOperation[] = [
      { op: 'delete', text: 'removed text' },
    ];

    const result = renderCharacterDiff(operations);
    const spans = result.querySelectorAll('span');

    expect(spans.length).toBe(1);
    expect(spans[0]?.textContent).toBe('removed text');
    expect(spans[0]?.className).toBe('bg-red-100 line-through text-red-800');
  });

  it('should render insert operations with correct styling', () => {
    const operations: DiffOperation[] = [
      { op: 'insert', text: 'added text' },
    ];

    const result = renderCharacterDiff(operations);
    const spans = result.querySelectorAll('span');

    expect(spans.length).toBe(1);
    expect(spans[0]?.textContent).toBe('added text');
    expect(spans[0]?.className).toBe('bg-green-100 font-semibold text-green-800');
  });

  it('should render mixed operations correctly', () => {
    const operations: DiffOperation[] = [
      { op: 'equal', text: 'Hello ' },
      { op: 'delete', text: 'world' },
      { op: 'insert', text: 'universe' },
      { op: 'equal', text: '!' },
    ];

    const result = renderCharacterDiff(operations);
    const spans = result.querySelectorAll('span');

    expect(spans.length).toBe(4);

    // Check first span (equal)
    expect(spans[0]?.textContent).toBe('Hello ');
    expect(spans[0]?.className).toBe('text-gray-700');

    // Check second span (delete)
    expect(spans[1]?.textContent).toBe('world');
    expect(spans[1]?.className).toBe('bg-red-100 line-through text-red-800');

    // Check third span (insert)
    expect(spans[2]?.textContent).toBe('universe');
    expect(spans[2]?.className).toBe('bg-green-100 font-semibold text-green-800');

    // Check fourth span (equal)
    expect(spans[3]?.textContent).toBe('!');
    expect(spans[3]?.className).toBe('text-gray-700');
  });

  it('should escape HTML special characters', () => {
    const operations: DiffOperation[] = [
      { op: 'equal', text: '<script>alert("xss")</script>' },
    ];

    const result = renderCharacterDiff(operations);
    const spans = result.querySelectorAll('span');

    // textContent automatically escapes HTML, so we check that no script tag was created
    expect(result.querySelector('script')).toBeNull();
    expect(spans[0]?.textContent).toBe('<script>alert("xss")</script>');
  });

  it('should handle empty operations array', () => {
    const operations: DiffOperation[] = [];
    const result = renderCharacterDiff(operations);

    expect(result).toBeInstanceOf(HTMLElement);
    expect(result.textContent).toBe('');
    expect(result.querySelectorAll('span').length).toBe(0);
  });

  it('should handle null/undefined operations gracefully', () => {
    // @ts-expect-error Testing runtime behavior with invalid input
    const result = renderCharacterDiff(null);

    expect(result).toBeInstanceOf(HTMLElement);
    expect(result.textContent).toBe('');
  });

  it('should skip operations with empty text', () => {
    const operations: DiffOperation[] = [
      { op: 'equal', text: 'Hello' },
      { op: 'equal', text: '' },
      { op: 'insert', text: 'World' },
    ];

    const result = renderCharacterDiff(operations);
    const spans = result.querySelectorAll('span');

    // Empty text operation should be skipped
    expect(spans.length).toBe(2);
    expect(spans[0]?.textContent).toBe('Hello');
    expect(spans[1]?.textContent).toBe('World');
  });

  it('should handle multiline text with preserved line breaks', () => {
    const operations: DiffOperation[] = [
      { op: 'equal', text: 'Line 1\nLine 2\nLine 3' },
    ];

    const result = renderCharacterDiff(operations);
    const spans = result.querySelectorAll('span');

    expect(spans[0]?.textContent).toBe('Line 1\nLine 2\nLine 3');
    // whitespace-pre-wrap should preserve line breaks
    expect(result.className).toContain('whitespace-pre-wrap');
  });

  it('should handle real-world scenario: punctuation change', () => {
    // Example: "Hello world" -> "Hello world."
    const operations: DiffOperation[] = [
      { op: 'equal', text: 'Hello world' },
      { op: 'insert', text: '.' },
    ];

    const result = renderCharacterDiff(operations);
    const spans = result.querySelectorAll('span');

    expect(spans.length).toBe(2);
    expect(spans[0]?.textContent).toBe('Hello world');
    expect(spans[0]?.className).toBe('text-gray-700');
    expect(spans[1]?.textContent).toBe('.');
    expect(spans[1]?.className).toBe('bg-green-100 font-semibold text-green-800');
  });

  it('should handle unknown operation types with fallback styling', () => {
    const operations = [
      { op: 'unknown' as 'equal', text: 'test' },
    ];

    const result = renderCharacterDiff(operations);
    const spans = result.querySelectorAll('span');

    expect(spans.length).toBe(1);
    expect(spans[0]?.className).toBe('text-gray-700'); // Falls back to equal styling
  });

  it('should handle operations with special characters', () => {
    const operations: DiffOperation[] = [
      { op: 'equal', text: 'Test & "quotes" <tags>' },
      { op: 'insert', text: '\' and \\ backslash' },
    ];

    const result = renderCharacterDiff(operations);
    const spans = result.querySelectorAll('span');

    expect(spans.length).toBe(2);
    expect(spans[0]?.textContent).toBe('Test & "quotes" <tags>');
    expect(spans[1]?.textContent).toBe('\' and \\ backslash');
    // Ensure no actual HTML tags were created
    expect(result.querySelector('tags')).toBeNull();
  });

  it('should maintain proper container structure', () => {
    const operations: DiffOperation[] = [
      { op: 'equal', text: 'test' },
    ];

    const result = renderCharacterDiff(operations);

    expect(result.tagName).toBe('DIV');
    expect(result.className).toContain('whitespace-pre-wrap');
    expect(result.className).toContain('break-words');
  });
});
