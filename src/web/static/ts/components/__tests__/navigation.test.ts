/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, it, expect } from 'vitest';
import { createNavbar, createSidebar } from '../navigation';

describe('Navigation Components', () => {
  it('should create a navbar', () => {
    const navbar = createNavbar({ brand: 'Test Brand' });
    expect(navbar).toBeInstanceOf(HTMLElement);
  });

  it('should create a sidebar', () => {
    const sidebar = createSidebar();
    expect(sidebar).toBeInstanceOf(HTMLElement);
  });

  // More tests to be added in Phase 2
});
