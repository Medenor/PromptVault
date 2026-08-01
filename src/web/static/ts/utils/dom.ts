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

const HTML_ESCAPE_MAP: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

/**
 * Escape HTML to prevent XSS.
 *
 * Escapes quote characters in addition to &, <, > so the result is safe to
 * interpolate into both text-node and double/single-quoted attribute-value
 * positions — a `textContent`/`innerHTML` round-trip only escapes the former.
 */
export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => HTML_ESCAPE_MAP[char] ?? char);
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

/**
 * Update scroll indicator classes based on scroll position
 */
function updateScrollIndicators(element: HTMLElement, wrapper: HTMLElement): void {
  const { scrollTop, scrollHeight, clientHeight } = element;
  const hasScroll = scrollHeight > clientHeight;
  const isScrolled = scrollTop > 0;
  const isAtBottom = scrollTop + clientHeight >= scrollHeight - 1;

  wrapper.classList.toggle('has-overflow', hasScroll);
  wrapper.classList.toggle('is-scrolled', isScrolled);
  wrapper.classList.toggle('at-bottom', isAtBottom);
}

/**
 * Setup scroll indicators for a container element
 * Adds gradient fade indicators at top/bottom based on scroll position
 * This function wraps the element in a container and adds overlay divs for the fade effect
 */
export function setupScrollIndicators(element: HTMLElement | null): void {
  if (!element) return;

  // Check if already wrapped (avoid double wrapping)
  if (element.parentElement?.classList.contains('scrollable-fade-wrapper')) {
    return;
  }

  // Add custom scrollbar class to the scrollable element
  element.classList.add('custom-scrollbar');

  // Create wrapper div
  const wrapper = document.createElement('div');
  wrapper.className = 'scrollable-fade-wrapper';

  // Create top fade overlay
  const topFade = document.createElement('div');
  topFade.className = 'scroll-fade-top';

  // Create bottom fade overlay
  const bottomFade = document.createElement('div');
  bottomFade.className = 'scroll-fade-bottom';

  // Insert wrapper before the element
  const parent = element.parentElement;
  if (!parent) return;

  parent.insertBefore(wrapper, element);

  // Move element into wrapper and add overlays
  wrapper.appendChild(element);
  wrapper.appendChild(topFade);
  wrapper.appendChild(bottomFade);

  // Create throttled scroll handler
  let ticking = false;
  const handleScroll = (): void => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        updateScrollIndicators(element, wrapper);
        ticking = false;
      });
      ticking = true;
    }
  };

  // Setup event listeners
  element.addEventListener('scroll', handleScroll, { passive: true });

  // Update on resize
  const resizeObserver = new ResizeObserver(() => {
    updateScrollIndicators(element, wrapper);
  });
  resizeObserver.observe(element);

  // Initial update
  updateScrollIndicators(element, wrapper);
}

/**
 * Setup scroll indicators for multiple elements matching a selector
 */
export function setupScrollIndicatorsForSelector(selector: string): void {
  querySelectorAll<HTMLElement>(selector).forEach((element) => {
    setupScrollIndicators(element);
  });
}
