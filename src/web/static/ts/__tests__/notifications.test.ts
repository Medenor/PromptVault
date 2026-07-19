import { describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => `tr:${key}`),
  },
}));

import {
  confirmAction,
  hideStatus,
  reportError,
  reportWarning,
  showLoading,
  showNotification,
  showStatus,
} from '@/utils/notifications';

describe('notifications utils', () => {
  it('uses translated message in confirmAction', () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    const result = confirmAction('messages.confirmDelete');

    expect(confirmSpy).toHaveBeenCalledWith('tr:messages.confirmDelete');
    expect(result).toBe(true);

    confirmSpy.mockRestore();
  });

  it('passes interpolation options through confirmAction', () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

    const result = confirmAction('messages.confirmDelete', { name: 'thing' });

    expect(confirmSpy).toHaveBeenCalledWith('tr:messages.confirmDelete');
    expect(result).toBe(false);

    confirmSpy.mockRestore();
  });

  it('shows loading text with translations', () => {
    document.body.innerHTML = '<div id="loading"></div>';

    showLoading('loading');

    const element = document.getElementById('loading');
    expect(element?.textContent).toBe('tr:messages.loading');
    expect(element?.classList.contains('hidden')).toBe(false);
  });

  it('shows loading with an explicit message', () => {
    document.body.innerHTML = '<div id="loading"></div>';

    showLoading('loading', 'Custom loading text');

    const element = document.getElementById('loading');
    expect(element?.textContent).toBe('Custom loading text');
  });

  it('does nothing when the loading element is missing', () => {
    document.body.innerHTML = '';
    expect(() => showLoading('missing')).not.toThrow();
  });

  it('shows and hides status messages', () => {
    document.body.innerHTML = '<div id="status" class="hidden"></div>';

    showStatus('status', 'Ok', 'success');
    const element = document.getElementById('status');
    expect(element?.textContent).toBe('Ok');
    expect(element?.classList.contains('hidden')).toBe(false);
    expect(element?.className).toContain('status-success');

    hideStatus('status');
    expect(element?.classList.contains('hidden')).toBe(true);
  });

  it('sets alert role and assertive aria-live for error status', () => {
    document.body.innerHTML = '<div id="status"></div>';

    showStatus('status', 'Failed', 'error');
    const element = document.getElementById('status');
    expect(element?.getAttribute('role')).toBe('alert');
    expect(element?.getAttribute('aria-live')).toBe('assertive');
  });

  it('defaults to info type when none is given', () => {
    document.body.innerHTML = '<div id="status"></div>';

    showStatus('status', 'Neutral');
    const element = document.getElementById('status');
    expect(element?.className).toContain('status-info');
  });

  it('does nothing when the status element is missing', () => {
    document.body.innerHTML = '';
    expect(() => showStatus('missing', 'text')).not.toThrow();
    expect(() => hideStatus('missing')).not.toThrow();
  });

  it('shows toast notifications', () => {
    vi.useFakeTimers();
    showNotification('Hello', 'warning', 10);

    const toast = document.querySelector('.notification');
    expect(toast?.textContent).toBe('Hello');
    expect(toast?.getAttribute('role')).toBe('status');

    vi.advanceTimersByTime(10);
    expect(document.querySelector('.notification')).toBeNull();
    vi.useRealTimers();
  });

  it('renders a success icon and non-alert status/polite attributes', () => {
    vi.useFakeTimers();
    showNotification('Saved', 'success', 10);

    const toast = document.querySelector('.notification-success');
    expect(toast?.getAttribute('role')).toBe('status');
    expect(toast?.getAttribute('aria-live')).toBe('polite');
    const icon = toast?.querySelector('svg.notification-icon path');
    expect(icon?.getAttribute('d')).toBe(
      'M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm-1 14.2-3.2-3.2 1.4-1.4 1.8 1.8 4.6-4.6 1.4 1.4Z'
    );

    vi.advanceTimersByTime(10);
    vi.useRealTimers();
  });

  it('renders an error icon with alert role and assertive aria-live', () => {
    vi.useFakeTimers();
    showNotification('Failed', 'error', 10);

    const toast = document.querySelector('.notification-error');
    expect(toast?.getAttribute('role')).toBe('alert');
    expect(toast?.getAttribute('aria-live')).toBe('assertive');
    const icon = toast?.querySelector('svg.notification-icon path');
    expect(icon?.getAttribute('d')).toBe(
      'M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm3.5 13.1-1.4 1.4L12 13.4l-2.1 2.1-1.4-1.4L10.6 12 8.5 9.9l1.4-1.4L12 10.6l2.1-2.1 1.4 1.4L13.4 12Z'
    );

    vi.advanceTimersByTime(10);
    vi.useRealTimers();
  });

  it('renders the default info icon for unrecognized/default type', () => {
    vi.useFakeTimers();
    showNotification('Info', 'info', 10);

    const toast = document.querySelector('.notification-info');
    expect(toast?.getAttribute('role')).toBe('status');
    const icon = toast?.querySelector('svg.notification-icon path');
    expect(icon?.getAttribute('d')).toBe(
      'M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm1 15h-2V11h2v6Zm0-8h-2V7h2v2Z'
    );

    vi.advanceTimersByTime(10);
    vi.useRealTimers();
  });

  it('reports errors and warnings via telemetry when available', () => {
    const reportErrorMock = vi.fn();
    const logger = {
      reportError: reportErrorMock,
    };
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});

    (window as unknown as { FrontendLogger?: typeof logger }).FrontendLogger = logger;

    reportError('test', 'action', new Error('boom'));
    reportWarning('test', 'warn', 'careful');

    expect(reportErrorMock).toHaveBeenCalledTimes(2);
    expect(consoleError).toHaveBeenCalled();
    expect(consoleWarn).toHaveBeenCalled();

    consoleError.mockRestore();
    consoleWarn.mockRestore();
    delete (window as unknown as { FrontendLogger?: typeof logger }).FrontendLogger;
  });

  it('logs to console without throwing when no telemetry logger is present', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    delete (window as unknown as { FrontendLogger?: unknown }).FrontendLogger;

    expect(() => reportError('test', 'action', new Error('boom'))).not.toThrow();
    expect(() => reportWarning('test', 'warn', 'careful')).not.toThrow();

    expect(consoleError).toHaveBeenCalled();
    expect(consoleWarn).toHaveBeenCalled();

    consoleError.mockRestore();
    consoleWarn.mockRestore();
  });

  it('does not call a logger without a reportError function', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    (window as unknown as { FrontendLogger?: unknown }).FrontendLogger = {};

    expect(() => reportError('test', 'action', new Error('boom'))).not.toThrow();

    consoleError.mockRestore();
    delete (window as unknown as { FrontendLogger?: unknown }).FrontendLogger;
  });
});
