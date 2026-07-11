/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  closeMobileDrawer,
  initKeyboardSafeScroll,
  initMobileNav,
  isMobileDrawerOpen,
  openMobileDrawer,
  toggleMobileDrawer,
} from '../mobile-nav';

function renderDrawerMarkup(): void {
  document.body.innerHTML = `
    <button id="mobile-menu-toggle" aria-label="Open menu">Menu</button>
    <div id="sidebar-backdrop" class="hidden"></div>
    <aside id="mobile-sidebar" class="-translate-x-full" role="dialog" aria-modal="true">
      <button id="sidebar-close" aria-label="Close sidebar">Close</button>
      <button id="sidebar-toggle">Toggle</button>
      <nav>
        <button id="new-prompt-btn-mobile">New Prompt</button>
        <button id="logout-btn-mobile">Logout</button>
      </nav>
    </aside>
  `;
}

describe('mobile-nav drawer', () => {
  beforeEach(() => {
    renderDrawerMarkup();
    document.body.style.overflow = '';
  });

  afterEach(() => {
    closeMobileDrawer();
    document.body.style.overflow = '';
  });

  it('is closed by default', () => {
    expect(isMobileDrawerOpen()).toBe(false);
  });

  it('opens the drawer, removes backdrop hidden class, and locks body scroll', () => {
    openMobileDrawer();

    const drawer = document.getElementById('mobile-sidebar')!;
    const backdrop = document.getElementById('sidebar-backdrop')!;

    expect(drawer.classList.contains('-translate-x-full')).toBe(false);
    expect(backdrop.classList.contains('hidden')).toBe(false);
    expect(document.body.style.overflow).toBe('hidden');
    expect(isMobileDrawerOpen()).toBe(true);
  });

  it('closes the drawer, restores backdrop hidden class, and unlocks body scroll', () => {
    openMobileDrawer();
    closeMobileDrawer();

    const drawer = document.getElementById('mobile-sidebar')!;
    const backdrop = document.getElementById('sidebar-backdrop')!;

    expect(drawer.classList.contains('-translate-x-full')).toBe(true);
    expect(backdrop.classList.contains('hidden')).toBe(true);
    expect(document.body.style.overflow).toBe('');
    expect(isMobileDrawerOpen()).toBe(false);
  });

  it('toggles open then closed', () => {
    toggleMobileDrawer();
    expect(isMobileDrawerOpen()).toBe(true);

    toggleMobileDrawer();
    expect(isMobileDrawerOpen()).toBe(false);
  });

  it('sets aria-expanded=true on both triggers when opened', () => {
    initMobileNav();
    openMobileDrawer();

    const toggle = document.getElementById('mobile-menu-toggle')!;
    const sidebarToggle = document.getElementById('sidebar-toggle')!;

    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(sidebarToggle.getAttribute('aria-expanded')).toBe('true');
  });

  it('sets aria-expanded=false on both triggers when closed', () => {
    initMobileNav();
    openMobileDrawer();
    closeMobileDrawer();

    const toggle = document.getElementById('mobile-menu-toggle')!;
    const sidebarToggle = document.getElementById('sidebar-toggle')!;

    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(sidebarToggle.getAttribute('aria-expanded')).toBe('false');
  });

  it('closes on Escape keydown while open', () => {
    openMobileDrawer();
    expect(isMobileDrawerOpen()).toBe(true);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));

    expect(isMobileDrawerOpen()).toBe(false);
  });

  it('closes when the backdrop is clicked', () => {
    initMobileNav();
    openMobileDrawer();

    const backdrop = document.getElementById('sidebar-backdrop')!;
    backdrop.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    expect(isMobileDrawerOpen()).toBe(false);
  });

  it('closes on outside tap (click outside drawer and toggles)', () => {
    initMobileNav();
    openMobileDrawer();

    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    expect(isMobileDrawerOpen()).toBe(false);
  });

  it('does not close when tapping inside the drawer', () => {
    initMobileNav();
    openMobileDrawer();

    const newPromptBtn = document.getElementById('new-prompt-btn-mobile')!;
    newPromptBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    expect(isMobileDrawerOpen()).toBe(true);
  });

  it('closes via the close button', () => {
    initMobileNav();
    openMobileDrawer();

    const closeBtn = document.getElementById('sidebar-close')!;
    closeBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    expect(isMobileDrawerOpen()).toBe(false);
  });

  it('does nothing when drawer markup is missing', () => {
    document.body.innerHTML = '';
    expect(() => openMobileDrawer()).not.toThrow();
    expect(() => closeMobileDrawer()).not.toThrow();
    expect(() => initMobileNav()).not.toThrow();
  });
});

describe('initKeyboardSafeScroll', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <input id="prompt-title" />
      <textarea id="prompt-content"></textarea>
    `;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('scrolls the focused field into view after a delay', () => {
    initKeyboardSafeScroll(['#prompt-title', '#prompt-content']);
    const title = document.getElementById('prompt-title') as HTMLInputElement;
    const scrollIntoViewSpy = vi.fn();
    title.scrollIntoView = scrollIntoViewSpy;

    title.dispatchEvent(new FocusEvent('focus'));
    vi.runAllTimers();

    expect(scrollIntoViewSpy).toHaveBeenCalledWith({ block: 'center', behavior: 'smooth' });
  });

  it('wires each selector independently', () => {
    initKeyboardSafeScroll(['#prompt-title', '#prompt-content']);
    const content = document.getElementById('prompt-content') as HTMLTextAreaElement;
    const scrollIntoViewSpy = vi.fn();
    content.scrollIntoView = scrollIntoViewSpy;

    content.dispatchEvent(new FocusEvent('focus'));
    vi.runAllTimers();

    expect(scrollIntoViewSpy).toHaveBeenCalled();
  });

  it('does nothing when the selector matches no element', () => {
    expect(() => initKeyboardSafeScroll(['#does-not-exist'])).not.toThrow();
  });
});
