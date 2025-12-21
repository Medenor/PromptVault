/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, it, expect } from 'vitest';
import { createFormGroup, createSelect } from '../form';

describe('Form Components', () => {
  it('should create a form group', () => {
    const input = document.createElement('input');
    const group = createFormGroup(input, { label: 'Test Label' });
    expect(group).toBeInstanceOf(HTMLDivElement);
  });

  it('should create a select element', () => {
    const select = createSelect({
      options: [
        { value: '1', label: 'Option 1' },
        { value: '2', label: 'Option 2' },
      ],
    });
    expect(select).toBeInstanceOf(HTMLSelectElement);
  });

  // More tests to be added in Phase 2
});
