/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, it, expect } from 'vitest';
import { createInput, createTextarea } from '../input';

describe('Input Component', () => {
  it('should create a basic input', () => {
    const input = createInput();
    expect(input).toBeInstanceOf(HTMLInputElement);
  });

  it('should create a basic textarea', () => {
    const textarea = createTextarea();
    expect(textarea).toBeInstanceOf(HTMLTextAreaElement);
  });

  // More tests to be added in Phase 2
});
