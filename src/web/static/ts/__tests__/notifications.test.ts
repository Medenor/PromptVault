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
    expect(toast?.getAttribute('role')).toBe('alert');

    vi.advanceTimersByTime(10);
    expect(document.querySelector('.notification')).toBeNull();
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
