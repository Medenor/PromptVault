/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { attachPullToRefresh, attachSwipeReveal } from '../gestures';

// jsdom does not implement PointerEvent; build a MouseEvent and attach the
// pointer-specific properties gestures.ts reads (pointerId, pointerType).
function pointerEvent(type: string, x: number, y: number, id = 1): PointerEvent {
  const event = new MouseEvent(type, { clientX: x, clientY: y, bubbles: true });
  Object.defineProperty(event, 'pointerId', { value: id });
  Object.defineProperty(event, 'pointerType', { value: 'touch' });
  return event as unknown as PointerEvent;
}

describe('attachSwipeReveal', () => {
  let card: HTMLElement;

  beforeEach(() => {
    document.body.innerHTML = '<div id="card"></div>';
    card = document.getElementById('card')!;
  });

  it('fires onSwipeLeft when dragged left past the threshold', () => {
    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();
    attachSwipeReveal(card, { onSwipeLeft, onSwipeRight });

    card.dispatchEvent(pointerEvent('pointerdown', 200, 100));
    card.dispatchEvent(pointerEvent('pointermove', 100, 100));
    card.dispatchEvent(pointerEvent('pointerup', 100, 100));

    expect(onSwipeLeft).toHaveBeenCalledWith(card);
    expect(onSwipeRight).not.toHaveBeenCalled();
  });

  it('fires onSwipeRight when dragged right past the threshold', () => {
    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();
    attachSwipeReveal(card, { onSwipeLeft, onSwipeRight });

    card.dispatchEvent(pointerEvent('pointerdown', 100, 100));
    card.dispatchEvent(pointerEvent('pointermove', 200, 100));
    card.dispatchEvent(pointerEvent('pointerup', 200, 100));

    expect(onSwipeRight).toHaveBeenCalledWith(card);
    expect(onSwipeLeft).not.toHaveBeenCalled();
  });

  it('does not fire either callback for a short drag under the threshold', () => {
    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();
    attachSwipeReveal(card, { onSwipeLeft, onSwipeRight });

    card.dispatchEvent(pointerEvent('pointerdown', 100, 100));
    card.dispatchEvent(pointerEvent('pointermove', 120, 100));
    card.dispatchEvent(pointerEvent('pointerup', 120, 100));

    expect(onSwipeLeft).not.toHaveBeenCalled();
    expect(onSwipeRight).not.toHaveBeenCalled();
  });

  it('abandons the gesture when vertical drift exceeds the limit (scrolling)', () => {
    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();
    attachSwipeReveal(card, { onSwipeLeft, onSwipeRight });

    card.dispatchEvent(pointerEvent('pointerdown', 200, 100));
    card.dispatchEvent(pointerEvent('pointermove', 100, 200));
    card.dispatchEvent(pointerEvent('pointerup', 100, 200));

    expect(onSwipeLeft).not.toHaveBeenCalled();
    expect(onSwipeRight).not.toHaveBeenCalled();
  });

  it('ignores events from a different pointerId', () => {
    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();
    attachSwipeReveal(card, { onSwipeLeft, onSwipeRight });

    card.dispatchEvent(pointerEvent('pointerdown', 200, 100, 1));
    card.dispatchEvent(pointerEvent('pointermove', 100, 100, 2));
    card.dispatchEvent(pointerEvent('pointerup', 100, 100, 2));

    expect(onSwipeLeft).not.toHaveBeenCalled();
  });

  it('detach removes all listeners', () => {
    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();
    const detach = attachSwipeReveal(card, { onSwipeLeft, onSwipeRight });
    detach();

    card.dispatchEvent(pointerEvent('pointerdown', 200, 100));
    card.dispatchEvent(pointerEvent('pointermove', 100, 100));
    card.dispatchEvent(pointerEvent('pointerup', 100, 100));

    expect(onSwipeLeft).not.toHaveBeenCalled();
  });
});

describe('attachPullToRefresh', () => {
  let container: HTMLElement;

  beforeEach(() => {
    document.body.innerHTML = '<div id="container"></div>';
    container = document.getElementById('container')!;
    Object.defineProperty(container, 'scrollTop', { value: 0, writable: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('triggers onRefresh with loading affordance when pulled past the threshold at scrollTop 0', async () => {
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    const showLoading = vi.fn();
    const hideLoading = vi.fn();
    attachPullToRefresh(container, { onRefresh, showLoading, hideLoading });

    container.dispatchEvent(pointerEvent('pointerdown', 100, 50));
    container.dispatchEvent(pointerEvent('pointerup', 100, 150));

    await vi.waitFor(() => expect(onRefresh).toHaveBeenCalled());
    expect(showLoading).toHaveBeenCalled();
    expect(hideLoading).toHaveBeenCalled();
  });

  it('does not trigger onRefresh for a short pull under the threshold', async () => {
    const onRefresh = vi.fn();
    const showLoading = vi.fn();
    const hideLoading = vi.fn();
    attachPullToRefresh(container, { onRefresh, showLoading, hideLoading });

    container.dispatchEvent(pointerEvent('pointerdown', 100, 50));
    container.dispatchEvent(pointerEvent('pointerup', 100, 80));

    expect(onRefresh).not.toHaveBeenCalled();
    expect(showLoading).not.toHaveBeenCalled();
  });

  it('does not start pulling when the container is already scrolled', async () => {
    Object.defineProperty(container, 'scrollTop', { value: 50, writable: true });
    const onRefresh = vi.fn();
    attachPullToRefresh(container, {
      onRefresh,
      showLoading: vi.fn(),
      hideLoading: vi.fn(),
    });

    container.dispatchEvent(pointerEvent('pointerdown', 100, 50));
    container.dispatchEvent(pointerEvent('pointerup', 100, 200));

    expect(onRefresh).not.toHaveBeenCalled();
  });

  it('hides the loading affordance even when onRefresh rejects', async () => {
    const onRefresh = vi.fn().mockRejectedValue(new Error('network error'));
    const showLoading = vi.fn();
    const hideLoading = vi.fn();
    attachPullToRefresh(container, { onRefresh, showLoading, hideLoading });

    container.dispatchEvent(pointerEvent('pointerdown', 100, 50));
    container.dispatchEvent(pointerEvent('pointerup', 100, 150));

    await vi.waitFor(() => expect(hideLoading).toHaveBeenCalled());
  });
});
