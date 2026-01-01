/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { DiffOperation } from '../types/api/responses';

/**
 * Render character-level diff operations as an HTML element
 *
 * @param operations - Array of diff operations (equal, delete, insert)
 * @returns HTMLElement containing the rendered diff with proper styling
 *
 * @example
 * ```ts
 * const ops = [
 *   { op: 'equal', text: 'Hello world' },
 *   { op: 'insert', text: '.' }
 * ];
 * const diffElement = renderCharacterDiff(ops);
 * document.body.appendChild(diffElement);
 * ```
 */
export function renderCharacterDiff(operations: DiffOperation[]): HTMLElement {
  const container = document.createElement('div');
  container.className = 'whitespace-pre-wrap break-words';

  if (!operations || operations.length === 0) {
    container.textContent = '';
    return container;
  }

  operations.forEach((op) => {
    if (!op || !op.text) {
      return;
    }

    const span = document.createElement('span');

    // Escape HTML and set text content
    span.textContent = op.text;

    // Apply styling based on operation type
    switch (op.op) {
      case 'equal':
        span.className = 'text-gray-700';
        break;
      case 'delete':
        span.className = 'bg-red-100 line-through text-red-800';
        break;
      case 'insert':
        span.className = 'bg-green-100 font-semibold text-green-800';
        break;
      default:
        // Fallback for unknown operation types
        span.className = 'text-gray-700';
    }

    container.appendChild(span);
  });

  return container;
}
