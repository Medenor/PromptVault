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
});
