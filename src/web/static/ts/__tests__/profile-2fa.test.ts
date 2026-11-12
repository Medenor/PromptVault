import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => key),
  },
}));

vi.mock('@/utils/i18n', () => ({
  t: vi.fn((key: string) => key),
}));

vi.mock('@/telemetry', () => ({
  reportError: vi.fn(),
}));

vi.mock('@/utils/notifications', () => ({
  showNotification: vi.fn(),
}));

vi.mock('@/utils/a11y', () => ({
  announce: vi.fn(),
}));

import { apiPost, APIRequestError } from '@/utils/api';
import { showNotification } from '@/utils/notifications';

vi.mock('@/utils/api', async () => {
  const actual = await vi.importActual<typeof import('@/utils/api')>('@/utils/api');
  return {
    ...actual,
    apiPost: vi.fn(),
  };
});

import { initProfileTwoFactor, __internal } from '../profile-2fa';

const mockedApiPost = vi.mocked(apiPost);
const mockedShowNotification = vi.mocked(showNotification);

function setupContainer(): void {
  document.body.innerHTML = '<div id="totp-2fa-card"></div>';
}

describe('profile-2fa', () => {
  beforeEach(() => {
    setupContainer();
    mockedApiPost.mockReset();
    mockedShowNotification.mockReset();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('renders the idle state with a start-enrollment button', () => {
    initProfileTwoFactor();

    const button = document.getElementById('totp-start-enrollment');
    expect(button).not.toBeNull();
  });

  it('start enrollment renders the QR code and manual secret', async () => {
    mockedApiPost.mockResolvedValueOnce({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri:
        'otpauth://totp/PromptVault:alice?secret=JBSWY3DPEHPK3PXP&issuer=PromptVault',
      qr_svg: '<svg><path d="M0 0"/></svg>',
    });

    initProfileTwoFactor();
    await __internal.startEnrollment();

    expect(mockedApiPost).toHaveBeenCalledWith('/api/auth/2fa/enroll');
    expect(document.getElementById('totp-manual-secret')?.textContent).toBe('JBSWY3DPEHPK3PXP');
    expect(document.getElementById('totp-qr-container')?.innerHTML).toContain('<svg>');
    expect(document.getElementById('totp-confirm-form')).not.toBeNull();
    expect(__internal.getPendingSecret()).toBe('JBSWY3DPEHPK3PXP');
  });

  it('ignores a second start while the first enroll request is in flight', async () => {
    let resolveEnroll: (value: unknown) => void = () => {};
    mockedApiPost.mockImplementationOnce(
      () => new Promise((resolve) => (resolveEnroll = resolve)) as never
    );

    initProfileTwoFactor();
    const first = __internal.startEnrollment();
    const second = __internal.startEnrollment(); // double-click / key repeat
    resolveEnroll({ secret: 'JBSWY3DPEHPK3PXP', provisioning_uri: 'x', qr_svg: '<svg></svg>' });
    await Promise.all([first, second]);

    expect(mockedApiPost).toHaveBeenCalledTimes(1);
  });

  it('moves focus to the scan step heading, and back to Start on cancel', async () => {
    mockedApiPost.mockResolvedValueOnce({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri: 'x',
      qr_svg: '<svg></svg>',
    });
    initProfileTwoFactor();
    document.getElementById('totp-start-enrollment')?.focus();

    await __internal.startEnrollment();

    // The start button is gone; focus must not fall back to <body>.
    expect(document.activeElement?.tagName).toBe('H3');

    document.getElementById('totp-cancel-enrollment')?.dispatchEvent(new Event('click'));
    expect(document.activeElement?.id).toBe('totp-start-enrollment');
  });

  it('shows an info notification and stays idle on 409 (already enabled)', async () => {
    mockedApiPost.mockRejectedValueOnce(
      new APIRequestError(409, { detail: 'Two-factor authentication is already enabled.' })
    );

    initProfileTwoFactor();
    await __internal.startEnrollment();

    expect(mockedShowNotification).toHaveBeenCalledWith(expect.any(String), 'info');
    expect(document.getElementById('totp-start-enrollment')).not.toBeNull();
  });

  it('confirm with a valid code shows recovery codes', async () => {
    mockedApiPost.mockResolvedValueOnce({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri:
        'otpauth://totp/PromptVault:alice?secret=JBSWY3DPEHPK3PXP&issuer=PromptVault',
      qr_svg: '<svg></svg>',
    });
    initProfileTwoFactor();
    await __internal.startEnrollment();

    const codeInput = document.getElementById('totp-confirm-code') as HTMLInputElement;
    codeInput.value = '123456';

    mockedApiPost.mockResolvedValueOnce({
      enabled: true,
      recovery_codes: [
        'ab12-cd34',
        'ef56-gh78',
        'ij90-kl12',
        'mn34-op56',
        'qr78-st90',
        'uv12-wx34',
        'yz56-ab78',
        'cd90-ef12',
        'gh34-ij56',
        'kl78-mn90',
      ],
    });

    await __internal.confirmEnrollment();

    expect(mockedApiPost).toHaveBeenLastCalledWith('/api/auth/2fa/verify', { code: '123456' });
    const list = document.getElementById('totp-recovery-codes-list');
    expect(list).not.toBeNull();
    expect(list?.querySelectorAll('li').length).toBe(10);
    expect(document.getElementById('totp-confirm-form')).toBeNull();
  });

  it('confirm with an invalid code shows an inline error and keeps the form', async () => {
    mockedApiPost.mockResolvedValueOnce({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri:
        'otpauth://totp/PromptVault:alice?secret=JBSWY3DPEHPK3PXP&issuer=PromptVault',
      qr_svg: '<svg></svg>',
    });
    initProfileTwoFactor();
    await __internal.startEnrollment();

    const codeInput = document.getElementById('totp-confirm-code') as HTMLInputElement;
    codeInput.value = '000000';

    mockedApiPost.mockRejectedValueOnce(
      new APIRequestError(401, { detail: 'Invalid or expired authentication code.' })
    );

    await __internal.confirmEnrollment();

    const errorEl = document.getElementById('totp-confirm-error');
    expect(errorEl?.classList.contains('hidden')).toBe(false);
    expect(errorEl?.textContent).not.toBe('');
    expect(document.getElementById('totp-confirm-form')).not.toBeNull();
  });

  it('confirm with an empty code shows a validation error without calling the API', async () => {
    mockedApiPost.mockResolvedValueOnce({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri:
        'otpauth://totp/PromptVault:alice?secret=JBSWY3DPEHPK3PXP&issuer=PromptVault',
      qr_svg: '<svg></svg>',
    });
    initProfileTwoFactor();
    await __internal.startEnrollment();

    mockedApiPost.mockClear();
    const codeInput = document.getElementById('totp-confirm-code') as HTMLInputElement;
    codeInput.value = '';

    await __internal.confirmEnrollment();

    expect(mockedApiPost).not.toHaveBeenCalled();
    const errorEl = document.getElementById('totp-confirm-error');
    expect(errorEl?.classList.contains('hidden')).toBe(false);
  });

  it('copy recovery codes writes joined codes to the clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    mockedApiPost.mockResolvedValueOnce({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri:
        'otpauth://totp/PromptVault:alice?secret=JBSWY3DPEHPK3PXP&issuer=PromptVault',
      qr_svg: '<svg></svg>',
    });
    initProfileTwoFactor();
    await __internal.startEnrollment();

    (document.getElementById('totp-confirm-code') as HTMLInputElement).value = '123456';
    mockedApiPost.mockResolvedValueOnce({
      enabled: true,
      recovery_codes: ['ab12-cd34', 'ef56-gh78'],
    });
    await __internal.confirmEnrollment();

    document.getElementById('totp-copy-recovery-codes')?.dispatchEvent(new Event('click'));
    await Promise.resolve();

    expect(writeText).toHaveBeenCalledWith('ab12-cd34\nef56-gh78');
  });

  it('download recovery codes triggers a Blob download', async () => {
    const clickSpy = vi.fn();
    const createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });

    mockedApiPost.mockResolvedValueOnce({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri:
        'otpauth://totp/PromptVault:alice?secret=JBSWY3DPEHPK3PXP&issuer=PromptVault',
      qr_svg: '<svg></svg>',
    });
    initProfileTwoFactor();
    await __internal.startEnrollment();

    (document.getElementById('totp-confirm-code') as HTMLInputElement).value = '123456';
    mockedApiPost.mockResolvedValueOnce({
      enabled: true,
      recovery_codes: ['ab12-cd34', 'ef56-gh78'],
    });
    await __internal.confirmEnrollment();

    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = originalCreateElement(tag);
      if (tag === 'a') {
        el.click = clickSpy;
      }
      return el;
    });

    document.getElementById('totp-download-recovery-codes')?.dispatchEvent(new Event('click'));

    expect(createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('cancel returns to the idle state', async () => {
    mockedApiPost.mockResolvedValueOnce({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri:
        'otpauth://totp/PromptVault:alice?secret=JBSWY3DPEHPK3PXP&issuer=PromptVault',
      qr_svg: '<svg></svg>',
    });
    initProfileTwoFactor();
    await __internal.startEnrollment();

    document.getElementById('totp-cancel-enrollment')?.dispatchEvent(new Event('click'));

    expect(document.getElementById('totp-start-enrollment')).not.toBeNull();
    expect(__internal.getPendingSecret()).toBeNull();
  });

  it('completing enrollment transitions to the manage view after Done', async () => {
    mockedApiPost.mockResolvedValueOnce({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri:
        'otpauth://totp/PromptVault:alice?secret=JBSWY3DPEHPK3PXP&issuer=PromptVault',
      qr_svg: '<svg></svg>',
    });
    initProfileTwoFactor();
    await __internal.startEnrollment();

    (document.getElementById('totp-confirm-code') as HTMLInputElement).value = '123456';
    mockedApiPost.mockResolvedValueOnce({
      enabled: true,
      recovery_codes: ['ab12-cd34', 'ef56-gh78'],
    });
    await __internal.confirmEnrollment();

    document.getElementById('totp-recovery-codes-done')?.dispatchEvent(new Event('click'));

    expect(__internal.isEnabled()).toBe(true);
    expect(document.getElementById('totp-disable-start')).not.toBeNull();
    expect(document.getElementById('totp-regenerate-start')).not.toBeNull();
  });

  describe('manage view (2FA already enabled)', () => {
    beforeEach(() => {
      initProfileTwoFactor(true);
    });

    it('renders disable and regenerate actions', () => {
      expect(document.getElementById('totp-disable-start')).not.toBeNull();
      expect(document.getElementById('totp-regenerate-start')).not.toBeNull();
      expect(document.getElementById('totp-start-enrollment')).toBeNull();
    });

    it('disable start shows the re-auth form', () => {
      document.getElementById('totp-disable-start')?.dispatchEvent(new Event('click'));

      expect(document.getElementById('totp-reauth-form')).not.toBeNull();
      expect(document.getElementById('totp-reauth-password')).not.toBeNull();
      expect(document.getElementById('totp-reauth-code')).not.toBeNull();
    });

    it('disable cancel returns to the manage view', () => {
      document.getElementById('totp-disable-start')?.dispatchEvent(new Event('click'));
      document.getElementById('totp-reauth-cancel')?.dispatchEvent(new Event('click'));

      expect(document.getElementById('totp-disable-start')).not.toBeNull();
      expect(document.getElementById('totp-reauth-form')).toBeNull();
    });

    it('disable with valid password and code disables 2FA', async () => {
      document.getElementById('totp-disable-start')?.dispatchEvent(new Event('click'));
      (document.getElementById('totp-reauth-password') as HTMLInputElement).value =
        'SecureP@ssw0rd123';
      (document.getElementById('totp-reauth-code') as HTMLInputElement).value = '123456';

      mockedApiPost.mockResolvedValueOnce({});

      await __internal.submitDisable();

      expect(mockedApiPost).toHaveBeenCalledWith('/api/auth/2fa/disable', {
        password: 'SecureP@ssw0rd123',
        code: '123456',
      });
      expect(__internal.isEnabled()).toBe(false);
      expect(document.getElementById('totp-start-enrollment')).not.toBeNull();
    });

    it('disable with wrong password/code shows an inline error and stays on the form', async () => {
      document.getElementById('totp-disable-start')?.dispatchEvent(new Event('click'));
      (document.getElementById('totp-reauth-password') as HTMLInputElement).value = 'wrong';
      (document.getElementById('totp-reauth-code') as HTMLInputElement).value = '000000';

      mockedApiPost.mockRejectedValueOnce(
        new APIRequestError(401, { detail: 'Incorrect password or authentication code.' })
      );

      await __internal.submitDisable();

      const errorEl = document.getElementById('totp-reauth-error');
      expect(errorEl?.classList.contains('hidden')).toBe(false);
      expect(errorEl?.textContent).not.toBe('');
      expect(document.getElementById('totp-reauth-form')).not.toBeNull();
      expect(__internal.isEnabled()).toBe(true);
    });

    it('disable with empty fields shows a validation error without calling the API', async () => {
      document.getElementById('totp-disable-start')?.dispatchEvent(new Event('click'));
      mockedApiPost.mockClear();

      await __internal.submitDisable();

      expect(mockedApiPost).not.toHaveBeenCalled();
      const errorEl = document.getElementById('totp-reauth-error');
      expect(errorEl?.classList.contains('hidden')).toBe(false);
    });

    it('regenerate start shows the re-auth form', () => {
      document.getElementById('totp-regenerate-start')?.dispatchEvent(new Event('click'));

      expect(document.getElementById('totp-reauth-form')).not.toBeNull();
    });

    it('regenerate with valid password and code shows new recovery codes', async () => {
      document.getElementById('totp-regenerate-start')?.dispatchEvent(new Event('click'));
      (document.getElementById('totp-reauth-password') as HTMLInputElement).value =
        'SecureP@ssw0rd123';
      (document.getElementById('totp-reauth-code') as HTMLInputElement).value = '123456';

      mockedApiPost.mockResolvedValueOnce({
        enabled: true,
        recovery_codes: ['zz11-zz22', 'yy33-yy44'],
      });

      await __internal.submitRegenerate();

      expect(mockedApiPost).toHaveBeenCalledWith('/api/auth/2fa/recovery-codes/regenerate', {
        password: 'SecureP@ssw0rd123',
        code: '123456',
      });
      const list = document.getElementById('totp-recovery-codes-list');
      expect(list).not.toBeNull();
      expect(list?.textContent).toContain('zz11-zz22');
    });

    it('regenerate with wrong password/code shows an inline error and stays on the form', async () => {
      document.getElementById('totp-regenerate-start')?.dispatchEvent(new Event('click'));
      (document.getElementById('totp-reauth-password') as HTMLInputElement).value = 'wrong';
      (document.getElementById('totp-reauth-code') as HTMLInputElement).value = '000000';

      mockedApiPost.mockRejectedValueOnce(
        new APIRequestError(401, { detail: 'Incorrect password or authentication code.' })
      );

      await __internal.submitRegenerate();

      const errorEl = document.getElementById('totp-reauth-error');
      expect(errorEl?.classList.contains('hidden')).toBe(false);
      expect(document.getElementById('totp-reauth-form')).not.toBeNull();
    });

    it('after regenerate, Done returns to the manage view', async () => {
      document.getElementById('totp-regenerate-start')?.dispatchEvent(new Event('click'));
      (document.getElementById('totp-reauth-password') as HTMLInputElement).value =
        'SecureP@ssw0rd123';
      (document.getElementById('totp-reauth-code') as HTMLInputElement).value = '123456';

      mockedApiPost.mockResolvedValueOnce({
        enabled: true,
        recovery_codes: ['zz11-zz22'],
      });
      await __internal.submitRegenerate();

      document.getElementById('totp-recovery-codes-done')?.dispatchEvent(new Event('click'));

      expect(document.getElementById('totp-disable-start')).not.toBeNull();
    });
  });
});
