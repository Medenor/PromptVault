/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, it, expect } from 'vitest';
import { createCard } from '../card';

describe('Card Component', () => {
  it('should create a basic card', () => {
    const card = createCard('Card content');
    expect(card).toBeInstanceOf(HTMLDivElement);
  });

  // More tests to be added in Phase 2
});
