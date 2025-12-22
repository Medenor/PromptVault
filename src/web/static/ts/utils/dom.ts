/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * DOM manipulation utilities with type safety
 */

const HIDDEN_CLASS = 'hidden';
const ERROR_VISIBLE_CLASS = 'validation-error-visible';
const FIELD_ERROR_CLASS = 'field-error';
const FIELD_WARNING_CLASS = 'field-warning';
const FIELD_VALID_CLASS = 'field-valid';

/**
 * Show an element by removing the hidden class
 */
export function showElement(element: HTMLElement | null): void {
  element?.classList.remove(HIDDEN_CLASS);
}

/**
 * Hide an element by adding the hidden class
 */
export function hideElement(element: HTMLElement | null): void {
  element?.classList.add(HIDDEN_CLASS);
}

/**
 * Toggle element visibility based on condition
 */
export function toggleElement(element: HTMLElement | null, shouldShow: boolean): void {
  element?.classList.toggle(HIDDEN_CLASS, !shouldShow);
}

/**
 * Get element by ID with type assertion
 */
export function getElementById<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

/**
 * Get required element by ID, throws if not found
 */
export function getRequiredElement<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id) as T | null;
  if (!element) {
    throw new Error(`Required element #${id} not found`);
  }
  return element;
}

/**
 * Query selector with type assertion
 */
export function querySelector<T extends Element>(
  selector: string,
  parent: ParentNode = document
): T | null {
  return parent.querySelector(selector) as T | null;
}

/**
 * Query selector all with type assertion
 */
export function querySelectorAll<T extends Element>(
  selector: string,
  parent: ParentNode = document
): NodeListOf<T> {
  return parent.querySelectorAll(selector) as NodeListOf<T>;
}

/**
 * Show validation error on an element
 */
export function showError(element: HTMLElement | null, message: string): void {
  if (element) {
    element.textContent = message;
    element.classList.add(ERROR_VISIBLE_CLASS);
  }
}

/**
 * Clear validation error from an element
 */
export function clearError(element: HTMLElement | null): void {
  if (element) {
    element.textContent = '';
    element.classList.remove(ERROR_VISIBLE_CLASS);
  }
}

/**
 * Clear all validation errors on the page
 */
export function clearAllErrors(): void {
  querySelectorAll<HTMLElement>('.validation-error').forEach((el) => {
    clearError(el);
  });
}

/**
 * Set field validation state classes
 */
export function setFieldState(
  field: HTMLElement | null,
  state: 'valid' | 'warning' | 'error' | 'pristine'
): void {
  if (!field) return;

  field.classList.remove(FIELD_ERROR_CLASS, FIELD_WARNING_CLASS, FIELD_VALID_CLASS);

  switch (state) {
    case 'valid':
      field.classList.add(FIELD_VALID_CLASS);
      break;
    case 'warning':
      field.classList.add(FIELD_WARNING_CLASS);
      break;
    case 'error':
      field.classList.add(FIELD_ERROR_CLASS);
      break;
    default:
      break;
  }
}

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Create element with attributes and children
 */
export function createElement<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attributes?: Record<string, string>,
  children?: Array<Node | string>
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);

  if (attributes) {
    for (const [key, value] of Object.entries(attributes)) {
      element.setAttribute(key, value);
    }
  }

  if (children) {
    for (const child of children) {
      if (typeof child === 'string') {
        element.appendChild(document.createTextNode(child));
      } else {
        element.appendChild(child);
      }
    }
  }

  return element;
}

/**
 * Debounce function execution
 */
export function debounce<T extends (...args: unknown[]) => void>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      fn(...args);
    }, delay);
  };
}
