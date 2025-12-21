/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { NavbarProps, SidebarProps, NavItemProps } from './types';

/**
 * Navigation Component Factories
 * Full implementation in Phase 2
 */

export function createNavbar(props?: NavbarProps): HTMLElement {
  const navbar = document.createElement('nav');

  const baseClasses = 'bg-white border-b border-border';
  const stickyClasses = props?.sticky ? 'sticky top-0 z-40' : '';

  navbar.className = `${baseClasses} ${stickyClasses} ${props?.className || ''}`.trim();

  const container = document.createElement('div');
  container.className = 'max-w-screen-xl mx-auto px-4 sm:px-6 lg:px-8';

  const wrapper = document.createElement('div');
  wrapper.className = 'flex items-center justify-between h-16';

  if (props?.brand) {
    const brand = document.createElement('div');
    brand.className = 'text-xl font-bold text-foreground';
    brand.textContent = props.brand;
    wrapper.appendChild(brand);
  }

  if (props?.items && props.items.length > 0) {
    const navItems = document.createElement('div');
    navItems.className = 'flex items-center space-x-4';

    props.items.forEach((item) => {
      const navItem = createNavItem(item);
      navItems.appendChild(navItem);
    });

    wrapper.appendChild(navItems);
  }

  container.appendChild(wrapper);
  navbar.appendChild(container);

  if (props?.id) navbar.id = props.id;

  return navbar;
}

export function createSidebar(props?: SidebarProps): HTMLElement {
  const sidebar = document.createElement('aside');

  const baseClasses = 'bg-white border-r border-border h-full';

  sidebar.className = `${baseClasses} ${props?.className || ''}`.trim();

  if (props?.items && props.items.length > 0) {
    const nav = document.createElement('nav');
    nav.className = 'p-4 space-y-2';

    props.items.forEach((item) => {
      const navItem = createNavItem(item, 'sidebar');
      nav.appendChild(navItem);
    });

    sidebar.appendChild(nav);
  }

  if (props?.id) sidebar.id = props.id;

  return sidebar;
}

function createNavItem(item: NavItemProps, variant: 'navbar' | 'sidebar' = 'navbar'): HTMLElement {
  const element = item.href ? document.createElement('a') : document.createElement('button');

  element.textContent = item.label;

  const baseClasses = variant === 'navbar'
    ? 'px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200'
    : 'w-full text-left px-4 py-2 text-sm font-medium rounded-md transition-colors duration-200';

  const activeClasses = item.active
    ? 'bg-primary text-white'
    : 'text-foreground hover:bg-gray-100';

  const disabledClasses = item.disabled ? 'opacity-50 cursor-not-allowed' : '';

  element.className = `${baseClasses} ${activeClasses} ${disabledClasses}`.trim();

  if (item.href && element instanceof HTMLAnchorElement) {
    element.href = item.href;
  }

  if (item.disabled) {
    element.setAttribute('disabled', 'true');
  }

  if (item.onClick && !item.disabled) {
    element.addEventListener('click', (e) => item.onClick?.(e as MouseEvent));
  }

  return element;
}
