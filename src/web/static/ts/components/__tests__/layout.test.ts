/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, it, expect } from 'vitest';
import { createContainer, createFlex, createGrid } from '../layout';

describe('Layout Components', () => {
  it('should create a container', () => {
    const container = createContainer('Content');
    expect(container).toBeInstanceOf(HTMLDivElement);
  });

  it('should create a flex container', () => {
    const flex = createFlex([document.createElement('div')]);
    expect(flex).toBeInstanceOf(HTMLDivElement);
  });

  it('should create a grid container', () => {
    const grid = createGrid([document.createElement('div')]);
    expect(grid).toBeInstanceOf(HTMLDivElement);
  });

  // More tests to be added in Phase 2
});
