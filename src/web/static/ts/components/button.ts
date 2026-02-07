/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { ButtonProps } from './types';

/**
 * Creates a styled button element using Tailwind CSS
 * @param label - Button text content
 * @param props - Button properties (variant, size, disabled, loading, etc.)
 * @returns HTMLButtonElement with Tailwind classes applied
 */
export function createButton(label: string, props: ButtonProps = {}): HTMLButtonElement {
  const button = document.createElement('button');
  button.type = props.type ?? 'button';
  button.textContent = label;

  // Base classes - consistent design system
  const baseClasses =
    'font-medium rounded-md transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2';

  // Variant classes - following design system colors
  const variantClasses: Record<string, string> = {
    primary: 'bg-blue-700 text-white hover:bg-blue-800 hover:scale-105 focus:ring-blue-700',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 hover:scale-105 focus:ring-gray-500',
    accent: 'bg-amber-700 text-white hover:bg-amber-800 hover:scale-105 focus:ring-amber-700',
    ghost:
      'bg-transparent text-gray-900 hover:bg-gray-100 border border-gray-300 focus:ring-gray-500',
    danger: 'bg-red-500 text-white hover:bg-red-600 hover:scale-105 focus:ring-red-500',
  };

  // Size classes - consistent spacing
  const sizeClasses: Record<string, string> = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  const variant = props.variant ?? 'primary';
  const size = props.size ?? 'md';

  // Apply classes
  let classList = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]}`;

  // Full width option
  if (props.fullWidth) {
    classList += ' w-full';
  }

  // Add custom className last (allows overrides)
  if (props.className) {
    classList += ` ${props.className}`;
  }

  button.className = classList.trim();

  // Handle disabled state
  if (props.disabled) {
    button.disabled = true;
    button.classList.add('opacity-50', 'cursor-not-allowed');
    button.classList.remove('hover:scale-105'); // Remove hover effects
  }

  // Handle loading state
  if (props.loading) {
    button.disabled = true;
    // Simple loading indicator (can be enhanced with spinner component)
    button.innerHTML = `<span class="inline-block animate-spin mr-2">⌛</span>${label}`;
    button.setAttribute('aria-busy', 'true');
  }

  // Add accessibility attributes
  if (props.ariaLabel) {
    button.setAttribute('aria-label', props.ariaLabel);
  }

  if (props.title) {
    button.title = props.title;
  }

  if (props.id) {
    button.id = props.id;
  }

  // Add click handler (only if not disabled)
  if (props.onClick && !props.disabled && !props.loading) {
    button.addEventListener('click', props.onClick);
  }

  return button;
}

/**
 * Creates a primary button (blue background)
 * @param label - Button text
 * @param onClick - Click handler
 * @returns Primary variant button
 */
export function createPrimaryButton(
  label: string,
  onClick?: (event: MouseEvent) => void
): HTMLButtonElement {
  return createButton(label, { variant: 'primary', ...(onClick && { onClick }) });
}

/**
 * Creates a secondary button (gray background)
 * @param label - Button text
 * @param onClick - Click handler
 * @returns Secondary variant button
 */
export function createSecondaryButton(
  label: string,
  onClick?: (event: MouseEvent) => void
): HTMLButtonElement {
  return createButton(label, { variant: 'secondary', ...(onClick && { onClick }) });
}

/**
 * Creates an accent button (amber background)
 * @param label - Button text
 * @param onClick - Click handler
 * @returns Accent variant button
 */
export function createAccentButton(
  label: string,
  onClick?: (event: MouseEvent) => void
): HTMLButtonElement {
  return createButton(label, { variant: 'accent', ...(onClick && { onClick }) });
}

/**
 * Creates a ghost button (transparent with border)
 * @param label - Button text
 * @param onClick - Click handler
 * @returns Ghost variant button
 */
export function createGhostButton(
  label: string,
  onClick?: (event: MouseEvent) => void
): HTMLButtonElement {
  return createButton(label, { variant: 'ghost', ...(onClick && { onClick }) });
}

/**
 * Creates a danger button (red background)
 * @param label - Button text
 * @param onClick - Click handler
 * @returns Danger variant button
 */
export function createDangerButton(
  label: string,
  onClick?: (event: MouseEvent) => void
): HTMLButtonElement {
  return createButton(label, { variant: 'danger', ...(onClick && { onClick }) });
}
