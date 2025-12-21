/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, it, expect } from 'vitest';
import { createNav, createTabs, createBreadcrumbs } from '../navigation';

describe('Navigation Components', () => {
  it('should create a nav', () => {
    const nav = createNav([
      { label: 'Home', href: '/' },
      { label: 'About', href: '/about' },
    ]);
    expect(nav).toBeInstanceOf(HTMLElement);
  });

  it('should create tabs', () => {
    const tabs = createTabs([
      { label: 'Tab 1', id: 'tab1', active: true, onClick: () => {} },
      { label: 'Tab 2', id: 'tab2', onClick: () => {} },
    ]);
    expect(tabs).toBeInstanceOf(HTMLDivElement);
  });

  it('should create breadcrumbs', () => {
    const breadcrumbs = createBreadcrumbs([
      { label: 'Home', href: '/' },
      { label: 'Products', href: '/products' },
      { label: 'Details', href: '/products/123' },
    ]);
    expect(breadcrumbs).toBeInstanceOf(HTMLElement);
  });
});
