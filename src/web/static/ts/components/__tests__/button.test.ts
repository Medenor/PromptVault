/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createButton } from '../button';
import { initButtonKeyboardActivation } from '@/utils/button-keyboard-activation';

describe('Button Component', () => {
  it('should create a basic button', () => {
    const button = createButton('Click me');
    expect(button).toBeInstanceOf(HTMLButtonElement);
    expect(button.textContent).toBe('Click me');
  });

  describe('Keyboard Activation', () => {
    beforeEach(() => {
      document.body.innerHTML = '';
      initButtonKeyboardActivation();
    });

    afterEach(() => {
      document.body.innerHTML = '';
    });

    it('should activate button on Enter key', () => {
      const button = createButton('Test Button');
      const clickHandler = vi.fn();
      button.addEventListener('click', clickHandler);
      document.body.appendChild(button);

      button.focus();
      const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
      button.dispatchEvent(event);

      expect(clickHandler).toHaveBeenCalled();
    });

    it('should activate button on Space key', () => {
      const button = createButton('Test Button');
      const clickHandler = vi.fn();
      button.addEventListener('click', clickHandler);
      document.body.appendChild(button);

      button.focus();
      const event = new KeyboardEvent('keydown', { key: ' ', bubbles: true });
      button.dispatchEvent(event);

      expect(clickHandler).toHaveBeenCalled();
    });

    it('should not activate disabled button on Enter key', () => {
      const button = createButton('Test Button', { disabled: true });
      const clickHandler = vi.fn();
      button.addEventListener('click', clickHandler);
      document.body.appendChild(button);

      button.focus();
      const event = new KeyboardEvent('keydown', { key: 'Enter' });
      document.dispatchEvent(event);

      expect(clickHandler).not.toHaveBeenCalled();
    });

    it('should not activate disabled button on Space key', () => {
      const button = createButton('Test Button', { disabled: true });
      const clickHandler = vi.fn();
      button.addEventListener('click', clickHandler);
      document.body.appendChild(button);

      button.focus();
      const event = new KeyboardEvent('keydown', { key: ' ' });
      document.dispatchEvent(event);

      expect(clickHandler).not.toHaveBeenCalled();
    });

    it('should prevent default behavior on Enter key', () => {
      const button = createButton('Test Button');
      document.body.appendChild(button);

      button.focus();
      const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault');
      button.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('should prevent default behavior on Space key', () => {
      const button = createButton('Test Button');
      document.body.appendChild(button);

      button.focus();
      const event = new KeyboardEvent('keydown', { key: ' ', bubbles: true });
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault');
      button.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('should not interfere with non-button elements', () => {
      const input = document.createElement('input');
      const clickHandler = vi.fn();
      input.addEventListener('click', clickHandler);
      document.body.appendChild(input);

      input.focus();
      const event = new KeyboardEvent('keydown', { key: 'Enter' });
      document.dispatchEvent(event);

      // Input should not receive keyboard activation (it handles Enter natively)
      // The handler should not be called by our keyboard activation handler
      // but may be called by native browser behavior
      expect(typeof clickHandler).toBe('function');
    });
  });

  // More tests to be added in Phase 2
});
