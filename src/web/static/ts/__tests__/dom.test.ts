import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearAllErrors,
  createElement,
  debounce,
  escapeHtml,
  getElementById,
  getRequiredElement,
  hideElement,
  querySelector,
  querySelectorAll,
  setFieldState,
  setupScrollIndicators,
  setupScrollIndicatorsForSelector,
  showError,
  showElement,
  toggleElement,
  clearError,
} from '@/utils/dom';

describe('dom utils', () => {
  it('toggles hidden class', () => {
    const element = document.createElement('div');
    element.classList.add('hidden');

    showElement(element);
    expect(element.classList.contains('hidden')).toBe(false);

    hideElement(element);
    expect(element.classList.contains('hidden')).toBe(true);

    toggleElement(element, true);
    expect(element.classList.contains('hidden')).toBe(false);

    toggleElement(element, false);
    expect(element.classList.contains('hidden')).toBe(true);
  });

  it('escapes HTML safely', () => {
    const html = '<script>alert("x")</script>';
    expect(escapeHtml(html)).toBe('&lt;script&gt;alert("x")&lt;/script&gt;');
  });

  it('clears validation errors', () => {
    document.body.innerHTML = `
      <span class="validation-error validation-error-visible">Oops</span>
      <span class="validation-error validation-error-visible">Nope</span>
    `;

    clearAllErrors();
    const errors = document.querySelectorAll('.validation-error');
    errors.forEach((el) => {
      expect(el.textContent).toBe('');
      expect(el.classList.contains('validation-error-visible')).toBe(false);
    });
  });

  it('gets elements safely and requires when missing', () => {
    document.body.innerHTML =
      '<div id="target"></div><span class="item"></span><span class="item"></span>';

    const byId = getElementById<HTMLDivElement>('target');
    expect(byId?.id).toBe('target');

    const items = querySelectorAll<HTMLSpanElement>('.item');
    expect(items.length).toBe(2);

    const first = querySelector<HTMLSpanElement>('.item');
    expect(first).not.toBeNull();

    expect(getRequiredElement<HTMLDivElement>('target')).toBeTruthy();
    expect(() => getRequiredElement<HTMLDivElement>('missing')).toThrow(
      'Required element #missing not found'
    );
  });

  it('handles error state helpers', () => {
    const element = document.createElement('div');
    showError(element, 'Oops');
    expect(element.textContent).toBe('Oops');
    expect(element.classList.contains('validation-error-visible')).toBe(true);

    clearError(element);
    expect(element.textContent).toBe('');
    expect(element.classList.contains('validation-error-visible')).toBe(false);
  });

  it('updates field state classes', () => {
    const field = document.createElement('input');

    setFieldState(field, 'error');
    expect(field.classList.contains('field-error')).toBe(true);

    setFieldState(field, 'warning');
    expect(field.classList.contains('field-warning')).toBe(true);

    setFieldState(field, 'valid');
    expect(field.classList.contains('field-valid')).toBe(true);

    setFieldState(field, 'pristine');
    expect(field.classList.contains('field-error')).toBe(false);
    expect(field.classList.contains('field-warning')).toBe(false);
    expect(field.classList.contains('field-valid')).toBe(false);
  });

  it('creates elements with attributes and children', () => {
    const child = document.createElement('span');
    child.textContent = 'child';
    const element = createElement('div', { 'data-test': 'ok' }, ['text', child]);

    expect(element.getAttribute('data-test')).toBe('ok');
    expect(element.textContent).toBe('textchild');
  });

  it('debounces calls', () => {
    vi.useFakeTimers();

    const fn = vi.fn();
    const debounced = debounce(fn, 200);

    debounced('a');
    debounced('b');

    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(200);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('b');

    vi.useRealTimers();
  });
});

describe('setupScrollIndicators', () => {
  let observedElements: HTMLElement[];
  let resizeCallbacks: Array<() => void>;
  let originalResizeObserver: typeof ResizeObserver | undefined;

  function setScrollMetrics(
    element: HTMLElement,
    metrics: { scrollTop?: number; scrollHeight?: number; clientHeight?: number }
  ): void {
    if (metrics.scrollTop !== undefined) {
      Object.defineProperty(element, 'scrollTop', { value: metrics.scrollTop, configurable: true });
    }
    if (metrics.scrollHeight !== undefined) {
      Object.defineProperty(element, 'scrollHeight', {
        value: metrics.scrollHeight,
        configurable: true,
      });
    }
    if (metrics.clientHeight !== undefined) {
      Object.defineProperty(element, 'clientHeight', {
        value: metrics.clientHeight,
        configurable: true,
      });
    }
  }

  beforeEach(() => {
    document.body.innerHTML = '';
    observedElements = [];
    resizeCallbacks = [];
    originalResizeObserver = globalThis.ResizeObserver;

    class FakeResizeObserver {
      private callback: () => void;

      constructor(callback: () => void) {
        this.callback = callback;
        resizeCallbacks.push(callback);
      }

      observe(element: HTMLElement): void {
        observedElements.push(element);
      }

      unobserve(): void {}
      disconnect(): void {}
    }

    vi.stubGlobal('ResizeObserver', FakeResizeObserver);
    vi.stubGlobal(
      'requestAnimationFrame',
      (cb: FrameRequestCallback): number => {
        cb(0);
        return 0;
      }
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    if (originalResizeObserver) {
      globalThis.ResizeObserver = originalResizeObserver;
    }
  });

  it('does nothing when element is null', () => {
    expect(() => setupScrollIndicators(null)).not.toThrow();
  });

  it('does nothing when the element is already wrapped', () => {
    const wrapper = document.createElement('div');
    wrapper.className = 'scrollable-fade-wrapper';
    const element = document.createElement('div');
    wrapper.appendChild(element);
    document.body.appendChild(wrapper);

    setupScrollIndicators(element);

    expect(wrapper.children.length).toBe(1);
    expect(wrapper.contains(element)).toBe(true);
  });

  it('does nothing when the element has no parent', () => {
    const element = document.createElement('div');
    expect(() => setupScrollIndicators(element)).not.toThrow();
  });

  it('wraps the element and adds fade overlay divs', () => {
    const parent = document.createElement('div');
    const element = document.createElement('div');
    parent.appendChild(element);
    document.body.appendChild(parent);

    setupScrollIndicators(element);

    const wrapper = element.parentElement;
    expect(wrapper?.classList.contains('scrollable-fade-wrapper')).toBe(true);
    expect(element.classList.contains('custom-scrollbar')).toBe(true);
    expect(wrapper?.querySelector('.scroll-fade-top')).not.toBeNull();
    expect(wrapper?.querySelector('.scroll-fade-bottom')).not.toBeNull();
    expect(wrapper?.parentElement).toBe(parent);
  });

  it('registers a ResizeObserver on the element and updates classes on the initial call', () => {
    const parent = document.createElement('div');
    const element = document.createElement('div');
    parent.appendChild(element);
    document.body.appendChild(parent);
    setScrollMetrics(element, { scrollTop: 0, scrollHeight: 200, clientHeight: 100 });

    setupScrollIndicators(element);

    expect(observedElements).toContain(element);
    const wrapper = element.parentElement as HTMLElement;
    expect(wrapper.classList.contains('has-overflow')).toBe(true);
    expect(wrapper.classList.contains('is-scrolled')).toBe(false);
  });

  it('updates scroll indicator classes when the ResizeObserver callback fires', () => {
    const parent = document.createElement('div');
    const element = document.createElement('div');
    parent.appendChild(element);
    document.body.appendChild(parent);
    setScrollMetrics(element, { scrollTop: 0, scrollHeight: 200, clientHeight: 100 });

    setupScrollIndicators(element);
    const wrapper = element.parentElement as HTMLElement;

    setScrollMetrics(element, { scrollTop: 100 });
    resizeCallbacks.forEach((cb) => cb());

    expect(wrapper.classList.contains('is-scrolled')).toBe(true);
    expect(wrapper.classList.contains('at-bottom')).toBe(true);
  });

  it('updates scroll indicator classes on scroll via the throttled handler', () => {
    const parent = document.createElement('div');
    const element = document.createElement('div');
    parent.appendChild(element);
    document.body.appendChild(parent);
    setScrollMetrics(element, { scrollTop: 0, scrollHeight: 200, clientHeight: 100 });

    setupScrollIndicators(element);
    const wrapper = element.parentElement as HTMLElement;

    setScrollMetrics(element, { scrollTop: 50 });
    element.dispatchEvent(new Event('scroll'));

    expect(wrapper.classList.contains('is-scrolled')).toBe(true);
    expect(wrapper.classList.contains('at-bottom')).toBe(false);
  });
});

describe('setupScrollIndicatorsForSelector', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe(): void {}
        unobserve(): void {}
        disconnect(): void {}
      }
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sets up scroll indicators for every element matching the selector', () => {
    document.body.innerHTML = `
      <div class="scrollable"></div>
      <div class="scrollable"></div>
    `;

    setupScrollIndicatorsForSelector('.scrollable');

    document.querySelectorAll('.scrollable').forEach((element) => {
      expect(element.parentElement?.classList.contains('scrollable-fade-wrapper')).toBe(true);
    });
  });

  it('does nothing when no elements match the selector', () => {
    expect(() => setupScrollIndicatorsForSelector('.missing')).not.toThrow();
  });
});
