/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Touch gesture primitives (FR-007, FR-008), per research.md's decision to use
 * native Pointer Events rather than a gesture library: swipe-reveal on prompt
 * cards (left -> delete, right -> edit) and pull-to-refresh on the prompt list.
 *
 * Every gesture-driven action also has a visible, non-gesture equivalent
 * control (FR-020) — this module only supplies the gesture shortcut, never the
 * sole way to trigger an action.
 */

const SWIPE_THRESHOLD_PX = 60;
const SWIPE_MAX_VERTICAL_PX = 30;
const PULL_THRESHOLD_PX = 70;

export interface SwipeRevealCallbacks {
  onSwipeLeft: (card: HTMLElement) => void;
  onSwipeRight: (card: HTMLElement) => void;
}

/**
 * Attaches swipe-left/swipe-right detection to a single card element.
 * A horizontal drag past SWIPE_THRESHOLD_PX (with limited vertical drift, so it
 * doesn't fight with vertical scrolling of long card content) fires the
 * corresponding callback; the card visually tracks the drag while active.
 */
export function attachSwipeReveal(card: HTMLElement, callbacks: SwipeRevealCallbacks): () => void {
  let startX = 0;
  let startY = 0;
  let currentX = 0;
  let dragging = false;
  let pointerId: number | null = null;

  function onPointerDown(event: PointerEvent): void {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    startX = event.clientX;
    startY = event.clientY;
    currentX = 0;
    dragging = true;
    pointerId = event.pointerId;
  }

  function onPointerMove(event: PointerEvent): void {
    if (!dragging || event.pointerId !== pointerId) return;
    const deltaX = event.clientX - startX;
    const deltaY = event.clientY - startY;

    if (Math.abs(deltaY) > SWIPE_MAX_VERTICAL_PX) {
      // Vertical drag (scrolling) — abandon the swipe gesture.
      dragging = false;
      card.style.transform = '';
      return;
    }

    currentX = deltaX;
    card.style.transform = `translateX(${deltaX}px)`;
  }

  function onPointerUp(event: PointerEvent): void {
    if (!dragging || event.pointerId !== pointerId) return;
    dragging = false;
    card.style.transform = '';

    if (currentX <= -SWIPE_THRESHOLD_PX) {
      callbacks.onSwipeLeft(card);
    } else if (currentX >= SWIPE_THRESHOLD_PX) {
      callbacks.onSwipeRight(card);
    }
    currentX = 0;
  }

  card.addEventListener('pointerdown', onPointerDown);
  card.addEventListener('pointermove', onPointerMove);
  card.addEventListener('pointerup', onPointerUp);
  card.addEventListener('pointercancel', onPointerUp);

  return () => {
    card.removeEventListener('pointerdown', onPointerDown);
    card.removeEventListener('pointermove', onPointerMove);
    card.removeEventListener('pointerup', onPointerUp);
    card.removeEventListener('pointercancel', onPointerUp);
  };
}

/**
 * Attaches pull-to-refresh to a scrollable container: a downward drag past
 * PULL_THRESHOLD_PX, started while the container is scrolled to the top,
 * triggers `onRefresh`. `showLoading`/`hideLoading` toggle a loading affordance.
 */
export function attachPullToRefresh(
  container: HTMLElement,
  callbacks: {
    onRefresh: () => void | Promise<void>;
    showLoading: () => void;
    hideLoading: () => void;
  }
): () => void {
  let startY = 0;
  let pulling = false;
  let pointerId: number | null = null;

  function onPointerDown(event: PointerEvent): void {
    if (container.scrollTop > 0) return;
    startY = event.clientY;
    pulling = true;
    pointerId = event.pointerId;
  }

  function onPointerMove(event: PointerEvent): void {
    if (!pulling || event.pointerId !== pointerId) return;
    if (container.scrollTop > 0) {
      pulling = false;
    }
  }

  async function onPointerUp(event: PointerEvent): Promise<void> {
    if (!pulling || event.pointerId !== pointerId) return;
    pulling = false;
    const deltaY = event.clientY - startY;

    if (deltaY >= PULL_THRESHOLD_PX) {
      callbacks.showLoading();
      try {
        await callbacks.onRefresh();
      } catch (error) {
        console.error('[gestures] pull-to-refresh failed', error);
      } finally {
        callbacks.hideLoading();
      }
    }
  }

  container.addEventListener('pointerdown', onPointerDown);
  container.addEventListener('pointermove', onPointerMove);
  container.addEventListener('pointerup', (e) => void onPointerUp(e));
  container.addEventListener('pointercancel', (e) => void onPointerUp(e));

  return () => {
    container.removeEventListener('pointerdown', onPointerDown);
    container.removeEventListener('pointermove', onPointerMove);
  };
}
