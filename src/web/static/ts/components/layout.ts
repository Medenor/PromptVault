/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { ContainerProps, FlexProps, GridProps, SectionProps } from './types';

/**
 * Creates a container with max-width and horizontal padding
 * @param content - Content to place in container
 * @param props - Container properties
 * @returns HTMLDivElement with container styling
 */
export function createContainer(
  content: HTMLElement | string,
  props?: ContainerProps
): HTMLDivElement {
  const container = document.createElement('div');

  const maxWidthClasses = getMaxWidthClasses(props?.maxWidth || 'xl');
  const paddingClasses = props?.padding !== false ? 'px-4 sm:px-6 lg:px-8' : '';

  container.className =
    `mx-auto ${maxWidthClasses} ${paddingClasses} ${props?.className || ''}`.trim();

  if (typeof content === 'string') {
    // eslint-disable-next-line no-restricted-properties -- generic component sink; no caller passes untrusted data as a string
    container.innerHTML = content;
  } else {
    container.appendChild(content);
  }

  if (props?.id) container.id = props.id;
  if (props?.ariaLabel) container.setAttribute('aria-label', props.ariaLabel);

  return container;
}

/**
 * Creates a section element with background and padding
 * @param backgroundColor - Optional background color (Tailwind class)
 * @param props - Section properties
 * @returns HTMLElement section
 */
export function createSection(backgroundColor?: string, props?: SectionProps): HTMLElement {
  const section = document.createElement('section');

  const bgClass = backgroundColor || props?.backgroundColor || '';
  const paddingClass = getPaddingClasses(props?.padding || 'md');

  section.className = `w-full ${bgClass} ${paddingClass} ${props?.className || ''}`.trim();

  if (props?.id) section.id = props.id;
  if (props?.ariaLabel) section.setAttribute('aria-label', props.ariaLabel);

  return section;
}

/**
 * Creates a flexbox container
 * @param direction - Flex direction (row or col)
 * @param gap - Gap between items
 * @param props - Additional flex properties
 * @returns HTMLDivElement with flex styling
 */
export function createFlex(
  direction?: 'row' | 'col',
  gap?: string,
  props?: FlexProps
): HTMLDivElement {
  const flex = document.createElement('div');

  const baseClasses = 'flex';
  const directionClasses = (direction || props?.direction) === 'col' ? 'flex-col' : 'flex-row';
  const justifyClasses = getJustifyClasses(props?.justify);
  const alignClasses = getAlignClasses(props?.align);
  const gapClasses = getGapClasses(gap || props?.gap);
  const wrapClasses = props?.wrap ? 'flex-wrap' : '';

  flex.className =
    `${baseClasses} ${directionClasses} ${justifyClasses} ${alignClasses} ${gapClasses} ${wrapClasses} ${props?.className || ''}`.trim();

  if (props?.id) flex.id = props.id;
  if (props?.ariaLabel) flex.setAttribute('aria-label', props.ariaLabel);

  return flex;
}

/**
 * Creates a grid container
 * @param cols - Number of columns
 * @param props - Grid properties
 * @returns HTMLDivElement with grid styling
 */
export function createGrid(cols?: number, props?: GridProps): HTMLDivElement {
  const grid = document.createElement('div');

  const baseClasses = 'grid';
  const colsClasses = getColsClasses(cols || props?.cols || 1);
  const gapClasses = getGapClasses(props?.gap);
  const rowsClasses = props?.rows ? `grid-rows-${props.rows}` : '';

  grid.className =
    `${baseClasses} ${colsClasses} ${gapClasses} ${rowsClasses} ${props?.className || ''}`.trim();

  if (props?.id) grid.id = props.id;
  if (props?.ariaLabel) grid.setAttribute('aria-label', props.ariaLabel);

  return grid;
}

/**
 * Creates a semantic header element
 * @param props - Header properties
 * @returns HTMLElement header
 */
export function createHeader(props?: ContainerProps): HTMLElement {
  const header = document.createElement('header');

  const baseClasses = 'w-full';
  header.className = `${baseClasses} ${props?.className || ''}`.trim();

  if (props?.id) header.id = props.id;
  if (props?.ariaLabel) header.setAttribute('aria-label', props.ariaLabel);

  return header;
}

/**
 * Creates a semantic footer element
 * @param props - Footer properties
 * @returns HTMLElement footer
 */
export function createFooter(props?: ContainerProps): HTMLElement {
  const footer = document.createElement('footer');

  const baseClasses = 'w-full';
  footer.className = `${baseClasses} ${props?.className || ''}`.trim();

  if (props?.id) footer.id = props.id;
  if (props?.ariaLabel) footer.setAttribute('aria-label', props.ariaLabel);

  return footer;
}

// Helper functions

function getMaxWidthClasses(maxWidth: string): string {
  const maxWidths: Record<string, string> = {
    sm: 'max-w-screen-sm',
    md: 'max-w-screen-md',
    lg: 'max-w-screen-lg',
    xl: 'max-w-screen-xl',
    '2xl': 'max-w-screen-2xl',
    full: 'max-w-full',
  };
  return maxWidths[maxWidth] || maxWidths['xl'] || '';
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

function getGapClasses(gap?: string): string {
  if (!gap) return '';
  const gaps: Record<string, string> = {
    xs: 'gap-1',
    sm: 'gap-2',
    md: 'gap-4',
    lg: 'gap-6',
    xl: 'gap-8',
  };
  return gaps[gap] || `gap-${gap}`;
}

function getColsClasses(cols: number): string {
  // Handle responsive grid (1 col on mobile, N cols on desktop)
  if (cols === 1) return 'grid-cols-1';
  return `grid-cols-1 md:grid-cols-${cols}`;
}

function getPaddingClasses(padding: string): string {
  const paddings: Record<string, string> = {
    none: '',
    sm: 'py-6 px-4',
    md: 'py-12 px-4',
    lg: 'py-16 px-4',
    xl: 'py-24 px-4',
  };
  return paddings[padding] || paddings['md'] || '';
}
