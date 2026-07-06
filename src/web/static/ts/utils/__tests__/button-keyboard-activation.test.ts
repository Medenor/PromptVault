/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { initButtonKeyboardActivation } from '../button-keyboard-activation';

describe('initButtonKeyboardActivation', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    initButtonKeyboardActivation();
  });

  it('clicks button on Enter key when target is a button', () => {
    const button = document.createElement('button');
    const clickSpy = vi.fn();
    button.addEventListener('click', clickSpy);
    document.body.appendChild(button);

    const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    Object.defineProperty(event, 'target', { value: button });
    document.dispatchEvent(event);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('clicks button on Space key when target is a button', () => {
    const button = document.createElement('button');
    const clickSpy = vi.fn();
    button.addEventListener('click', clickSpy);
    document.body.appendChild(button);

    const event = new KeyboardEvent('keydown', { key: ' ', bubbles: true });
    Object.defineProperty(event, 'target', { value: button });
    document.dispatchEvent(event);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('does not click disabled button', () => {
    const button = document.createElement('button');
    button.disabled = true;
    const clickSpy = vi.fn();
    button.addEventListener('click', clickSpy);
    document.body.appendChild(button);

    const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    Object.defineProperty(event, 'target', { value: button });
    document.dispatchEvent(event);

    expect(clickSpy).not.toHaveBeenCalled();
  });

  it('does nothing when target is not a button', () => {
    const span = document.createElement('span');
    const clickSpy = vi.fn();
    span.addEventListener('click', clickSpy);
    document.body.appendChild(span);

    const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    Object.defineProperty(event, 'target', { value: span });
    document.dispatchEvent(event);

    expect(clickSpy).not.toHaveBeenCalled();
  });

  it('does nothing when target is null', () => {
    const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    Object.defineProperty(event, 'target', { value: null });
    expect(() => document.dispatchEvent(event)).not.toThrow();
  });

  it('does not activate on non-Enter/Space keys', () => {
    const button = document.createElement('button');
    const clickSpy = vi.fn();
    button.addEventListener('click', clickSpy);
    document.body.appendChild(button);

    const event = new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true });
    Object.defineProperty(event, 'target', { value: button });
    document.dispatchEvent(event);

    expect(clickSpy).not.toHaveBeenCalled();
  });
});
