/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { NavItemProps, TabsProps, BreadcrumbsProps } from './types';

/**
 * Creates a navigation menu
 * @param items - Navigation items
 * @param props - Additional properties
 * @returns nav element with items
 */
export function createNav(items: NavItemProps[], props?: any): HTMLElement {
  const nav = document.createElement('nav');

  nav.className = `flex items-center gap-4 ${props?.className || ''}`.trim();
  nav.setAttribute('role', 'navigation');

  if (props?.id) nav.id = props.id;
  if (props?.ariaLabel) nav.setAttribute('aria-label', props.ariaLabel);

  items.forEach((item) => {
    const navItem = createNavItem(item);
    nav.appendChild(navItem);
  });

  return nav;
}

/**
 * Creates a tab navigation component
 * @param tabs - Array of tab items
 * @param props - Additional properties
 * @returns div containing tabs
 */
export function createTabs(
  tabs: Array<{ label: string; id: string; active?: boolean; onClick: () => void }>,
  props?: TabsProps
): HTMLDivElement {
  const tabsContainer = document.createElement('div');
  tabsContainer.className = `border-b border-gray-200 ${props?.className || ''}`.trim();
  tabsContainer.setAttribute('role', 'tablist');

  if (props?.id) tabsContainer.id = props.id;
  if (props?.ariaLabel) tabsContainer.setAttribute('aria-label', props.ariaLabel);

  const tabList = document.createElement('div');
  tabList.className = 'flex gap-2';

  tabs.forEach((tab) => {
    const tabButton = document.createElement('button');
    tabButton.type = 'button';
    tabButton.textContent = tab.label;
    tabButton.setAttribute('role', 'tab');
    tabButton.setAttribute('aria-selected', tab.active ? 'true' : 'false');
    tabButton.setAttribute('aria-controls', tab.id);
    tabButton.id = `tab-${tab.id}`;

    // Base styling
    const baseClasses = 'px-4 py-2 font-medium text-sm transition-all duration-200 border-b-2';

    // Active/inactive states
    const stateClasses = tab.active
      ? 'border-blue-500 text-blue-600'
      : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300';

    tabButton.className = `${baseClasses} ${stateClasses}`.trim();

    tabButton.addEventListener('click', () => {
      // Update active states
      tabs.forEach((t, i) => {
        const btn = tabList.children[i] as HTMLButtonElement;
        if (t.id === tab.id) {
          btn.classList.remove(
            'border-transparent',
            'text-gray-600',
            'hover:text-gray-900',
            'hover:border-gray-300'
          );
          btn.classList.add('border-blue-500', 'text-blue-600');
          btn.setAttribute('aria-selected', 'true');
        } else {
          btn.classList.remove('border-blue-500', 'text-blue-600');
          btn.classList.add(
            'border-transparent',
            'text-gray-600',
            'hover:text-gray-900',
            'hover:border-gray-300'
          );
          btn.setAttribute('aria-selected', 'false');
        }
      });

      // Call the tab's onClick handler
      tab.onClick();
    });

    tabList.appendChild(tabButton);
  });

  tabsContainer.appendChild(tabList);

  return tabsContainer;
}

/**
 * Creates a breadcrumb navigation
 * @param items - Breadcrumb items
 * @param props - Additional properties
 * @returns nav element with breadcrumbs
 */
export function createBreadcrumbs(
  items: Array<{ label: string; href: string }>,
  props?: BreadcrumbsProps
): HTMLElement {
  const nav = document.createElement('nav');
  nav.className = `flex items-center gap-2 text-sm ${props?.className || ''}`.trim();
  nav.setAttribute('aria-label', 'Breadcrumb');

  if (props?.id) nav.id = props.id;

  const ol = document.createElement('ol');
  ol.className = 'flex items-center gap-2';

  items.forEach((item, index) => {
    const li = document.createElement('li');
    li.className = 'flex items-center gap-2';

    // Add separator before all items except the first
    if (index > 0) {
      const separator = document.createElement('span');
      separator.textContent = props?.separator || '/';
      separator.className = 'text-gray-400';
      separator.setAttribute('aria-hidden', 'true');
      li.appendChild(separator);
    }

    // Last item is current page (not a link)
    if (index === items.length - 1) {
      const current = document.createElement('span');
      current.textContent = item.label;
      current.className = 'text-gray-900 font-medium';
      current.setAttribute('aria-current', 'page');
      li.appendChild(current);
    } else {
      // Earlier items are links
      const link = document.createElement('a');
      link.href = item.href;
      link.textContent = item.label;
      link.className =
        'text-blue-600 hover:text-blue-800 hover:underline transition-colors duration-200';
      li.appendChild(link);
    }

    ol.appendChild(li);
  });

  nav.appendChild(ol);

  return nav;
}

/**
 * Creates a navigation item (link or button)
 * @param item - Navigation item properties
 * @returns HTMLElement (anchor or button)
 */
function createNavItem(item: NavItemProps): HTMLElement {
  const element = item.href ? document.createElement('a') : document.createElement('button');

  element.textContent = item.label;

  // Base styling
  const baseClasses = 'px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200';

  // Active/inactive states
  const stateClasses = item.active ? 'bg-blue-500 text-white' : 'text-gray-900 hover:bg-gray-100';

  // Disabled state
  const disabledClasses = item.disabled ? 'opacity-50 cursor-not-allowed pointer-events-none' : '';

  element.className = `${baseClasses} ${stateClasses} ${disabledClasses}`.trim();

  // Set href for links
  if (item.href && element instanceof HTMLAnchorElement) {
    element.href = item.href;
  }

  // Add disabled attribute for buttons
  if (item.disabled && element instanceof HTMLButtonElement) {
    element.disabled = true;
  }

  // Add click handler
  if (item.onClick && !item.disabled) {
    element.addEventListener('click', (e) => {
      item.onClick?.(e as MouseEvent);
    });
  }

  // Accessibility
  if (item.active) {
    element.setAttribute('aria-current', 'page');
  }

  return element;
}
