/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, it, expect } from 'vitest';
import {
  createContainer,
  createFlex,
  createGrid,
  createSection,
  createHeader,
  createFooter,
} from '../layout';

describe('Layout Components', () => {
  it('should create a container', () => {
    const container = createContainer('Content');
    expect(container).toBeInstanceOf(HTMLDivElement);
  });

  it('should create a flex container', () => {
    const flex = createFlex('row', 'md');
    expect(flex).toBeInstanceOf(HTMLDivElement);
  });

  it('should create a grid container', () => {
    const grid = createGrid(3);
    expect(grid).toBeInstanceOf(HTMLDivElement);
  });

  it('should create a section', () => {
    const section = createSection('bg-gray-100');
    expect(section).toBeInstanceOf(HTMLElement);
  });

  it('should create a header', () => {
    const header = createHeader();
    expect(header).toBeInstanceOf(HTMLElement);
  });

  it('should create a footer', () => {
    const footer = createFooter();
    expect(footer).toBeInstanceOf(HTMLElement);
  });
});
