/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { ContainerProps, FlexProps, GridProps } from './types';

/**
 * Layout Component Factories
 * Full implementation in Phase 2
 */

export function createContainer(content: HTMLElement | string, props?: ContainerProps): HTMLDivElement {
  const container = document.createElement('div');

  const maxWidthClasses = getMaxWidthClasses(props?.maxWidth || 'xl');
  const paddingClasses = props?.padding !== false ? 'px-4 sm:px-6 lg:px-8' : '';

  container.className = `mx-auto ${maxWidthClasses} ${paddingClasses} ${props?.className || ''}`.trim();

  if (typeof content === 'string') {
    container.innerHTML = content;
  } else {
    container.appendChild(content);
  }

  if (props?.id) container.id = props.id;

  return container;
}

export function createFlex(children: HTMLElement[], props?: FlexProps): HTMLDivElement {
  const flex = document.createElement('div');

  const baseClasses = 'flex';
  const directionClasses = props?.direction === 'col' ? 'flex-col' : 'flex-row';
  const justifyClasses = getJustifyClasses(props?.justify);
  const alignClasses = getAlignClasses(props?.align);
  const gapClasses = props?.gap ? `gap-${props.gap}` : '';
  const wrapClasses = props?.wrap ? 'flex-wrap' : '';

  flex.className = `${baseClasses} ${directionClasses} ${justifyClasses} ${alignClasses} ${gapClasses} ${wrapClasses} ${props?.className || ''}`.trim();

  children.forEach((child) => flex.appendChild(child));

  if (props?.id) flex.id = props.id;

  return flex;
}

export function createGrid(children: HTMLElement[], props?: GridProps): HTMLDivElement {
  const grid = document.createElement('div');

  const baseClasses = 'grid';
  const colsClasses = props?.cols ? `grid-cols-${props.cols}` : 'grid-cols-1';
  const gapClasses = props?.gap ? `gap-${props.gap}` : '';
  const rowsClasses = props?.rows ? `grid-rows-${props.rows}` : '';

  grid.className = `${baseClasses} ${colsClasses} ${gapClasses} ${rowsClasses} ${props?.className || ''}`.trim();

  children.forEach((child) => grid.appendChild(child));

  if (props?.id) grid.id = props.id;

  return grid;
}

function getMaxWidthClasses(maxWidth: string): string {
  const maxWidths: Record<string, string> = {
    sm: 'max-w-screen-sm',
    md: 'max-w-screen-md',
    lg: 'max-w-screen-lg',
    xl: 'max-w-screen-xl',
    '2xl': 'max-w-screen-2xl',
    full: 'max-w-full',
  };
  return maxWidths[maxWidth] ?? maxWidths['xl'] ?? '';
}

function getJustifyClasses(justify?: string): string {
  if (!justify) return '';
  const justifies: Record<string, string> = {
    start: 'justify-start',
    end: 'justify-end',
    center: 'justify-center',
    between: 'justify-between',
    around: 'justify-around',
    evenly: 'justify-evenly',
  };
  return justifies[justify] || '';
}

function getAlignClasses(align?: string): string {
  if (!align) return '';
  const aligns: Record<string, string> = {
    start: 'items-start',
    end: 'items-end',
    center: 'items-center',
    baseline: 'items-baseline',
    stretch: 'items-stretch',
  };
  return aligns[align] || '';
}
