import { describe, expect, it, vi } from 'vitest';
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
  showError,
  showElement,
  toggleElement,
  clearError,
} from '@/utils/dom';

describe('dom utils', () => {
  it('toggles hidden class', () => {
    const element = document.createElement('div');
    element.classList.add('is-hidden');

    showElement(element);
    expect(element.classList.contains('is-hidden')).toBe(false);

    hideElement(element);
    expect(element.classList.contains('is-hidden')).toBe(true);

    toggleElement(element, true);
    expect(element.classList.contains('is-hidden')).toBe(false);

    toggleElement(element, false);
    expect(element.classList.contains('is-hidden')).toBe(true);
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
