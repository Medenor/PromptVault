/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, it, expect } from 'vitest';
import { createButton } from '../button';

describe('Button Component', () => {
  it('should create a basic button', () => {
    const button = createButton('Click me');
    expect(button).toBeInstanceOf(HTMLButtonElement);
    expect(button.textContent).toBe('Click me');
  });

  // More tests to be added in Phase 2
});
