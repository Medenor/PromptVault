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

  it('shows loading text with translations', () => {
    document.body.innerHTML = '<div id="loading"></div>';

    showLoading('loading');

    const element = document.getElementById('loading');
    expect(element?.textContent).toBe('tr:messages.loading');
    expect(element?.classList.contains('hidden')).toBe(false);
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
});
