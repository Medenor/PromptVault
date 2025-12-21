/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { CardProps } from './types';

/**
 * Creates a card component with Tailwind CSS styling
 * @param content - HTML content or element to display in card
 * @param props - Card properties (variant, padding, clickable, etc.)
 * @returns HTMLDivElement with card styling
 */
export function createCard(content: HTMLElement | string, props: CardProps = {}): HTMLDivElement {
  const card = document.createElement('div');

  // Base classes
  const baseClasses = 'rounded-lg transition-all duration-200';

  // Variant classes
  const variantClasses: Record<string, string> = {
    default: 'bg-white',
    bordered: 'bg-white border border-gray-200',
    elevated: 'bg-white shadow-md hover:shadow-lg',
    colored: props.backgroundColor ? props.backgroundColor : 'bg-blue-50',
  };

  // Padding classes
  const paddingClasses: Record<string, string> = {
    compact: 'p-4',
    default: 'p-6',
    generous: 'p-8',
  };

  const variant = props.variant ?? 'default';
  const padding = props.padding ?? 'default';

  // Build class list
  let classList = `${baseClasses} ${variantClasses[variant]} ${paddingClasses[padding]}`;

  // Clickable cards get hover effects and cursor
  if (props.clickable) {
    classList += ' cursor-pointer hover:scale-[1.02] group';
  }

  // Add custom className last
  if (props.className) {
    classList += ` ${props.className}`;
  }

  card.className = classList.trim();

  // Add title if provided
  if (props.title) {
    const titleElement = document.createElement('h3');
    titleElement.textContent = props.title;
    titleElement.className = 'text-xl font-bold text-gray-900 mb-2';
    card.appendChild(titleElement);
  }

  // Add description if provided
  if (props.description) {
    const descElement = document.createElement('p');
    descElement.textContent = props.description;
    descElement.className = 'text-sm text-gray-600 mb-4';
    card.appendChild(descElement);
  }

  // Add main content
  const contentContainer = document.createElement('div');
  if (typeof content === 'string') {
    contentContainer.innerHTML = content;
  } else {
    contentContainer.appendChild(content);
  }
  card.appendChild(contentContainer);

  // Add footer if provided
  if (props.footer) {
    const footerElement = document.createElement('div');
    footerElement.className = 'mt-4 pt-4 border-t border-gray-200';
    if (typeof props.footer === 'string') {
      footerElement.innerHTML = props.footer;
    } else {
      footerElement.appendChild(props.footer);
    }
    card.appendChild(footerElement);
  }

  // Add ID and ARIA attributes
  if (props.id) {
    card.id = props.id;
  }

  if (props.ariaLabel) {
    card.setAttribute('aria-label', props.ariaLabel);
  }

  // Add click handler
  if (props.onClick) {
    card.addEventListener('click', props.onClick);
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');

    // Keyboard support for clickable cards
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        props.onClick?.(e as unknown as MouseEvent);
      }
    });
  }

  return card;
}

/**
 * Creates a white card with default styling
 * @param content - Card content
 * @param props - Additional card properties
 * @returns White card component
 */
export function createWhiteCard(content: HTMLElement | string, props: CardProps = {}): HTMLDivElement {
  return createCard(content, { ...props, variant: 'default' });
}

/**
 * Creates a colored card with custom background
 * @param content - Card content
 * @param color - Tailwind background color class (e.g., 'bg-blue-50', 'bg-green-50')
 * @param props - Additional card properties
 * @returns Colored card component
 */
export function createColoredCard(
  content: HTMLElement | string,
  color: string,
  props: CardProps = {}
): HTMLDivElement {
  return createCard(content, { ...props, variant: 'colored', backgroundColor: color });
}

/**
 * Creates an elevated card with shadow
 * @param content - Card content
 * @param props - Additional card properties
 * @returns Elevated card with shadow
 */
export function createElevatedCard(content: HTMLElement | string, props: CardProps = {}): HTMLDivElement {
  return createCard(content, { ...props, variant: 'elevated' });
}

/**
 * Creates a bordered card
 * @param content - Card content
 * @param props - Additional card properties
 * @returns Bordered card component
 */
export function createBorderedCard(content: HTMLElement | string, props: CardProps = {}): HTMLDivElement {
  return createCard(content, { ...props, variant: 'bordered' });
}
