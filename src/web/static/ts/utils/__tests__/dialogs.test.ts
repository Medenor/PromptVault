/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

let mockModalClickHandlers: Record<string, () => void> = {};
let mockOnClose: (() => void) | null = null;
let mockModalElement: HTMLElement;

vi.mock('@/components/modal', () => ({
  createModal: vi.fn((props: {
    title: string;
    content: HTMLElement;
    size: string;
    actions: Array<{ label: string; variant: string; onClick: () => void }>;
    onClose: () => void;
  }) => {
    mockModalElement = document.createElement('div');
    mockModalClickHandlers = {};
    mockOnClose = props.onClose;

    for (const action of props.actions) {
      mockModalClickHandlers[action.label] = action.onClick;
    }

    return {
      element: mockModalElement,
      open: vi.fn(),
      close: vi.fn(),
    };
  }),
}));

import { alertAsync, confirmAsync } from '../dialogs';

describe('confirmAsync', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    mockModalClickHandlers = {};
    mockOnClose = null;
  });

  it('resolves true when confirm button is clicked', async () => {
    const promise = confirmAsync({
      title: 'Confirm',
      message: 'Are you sure?',
      confirmLabel: 'Yes',
      cancelLabel: 'No',
    });

    mockModalClickHandlers['Yes']?.();

    const result = await promise;
    expect(result).toBe(true);
  });

  it('resolves false when cancel button is clicked', async () => {
    const promise = confirmAsync({
      title: 'Confirm',
      message: 'Are you sure?',
      confirmLabel: 'Yes',
      cancelLabel: 'No',
    });

    mockModalClickHandlers['No']?.();

    const result = await promise;
    expect(result).toBe(false);
  });

  it('resolves false when modal is closed via onClose', async () => {
    const promise = confirmAsync({
      title: 'Confirm',
      message: 'Are you sure?',
      confirmLabel: 'Yes',
      cancelLabel: 'No',
    });

    mockOnClose?.();

    const result = await promise;
    expect(result).toBe(false);
  });

  it('only settles once (idempotent)', async () => {
    const promise = confirmAsync({
      title: 'Confirm',
      message: 'Are you sure?',
      confirmLabel: 'Yes',
      cancelLabel: 'No',
    });

    mockModalClickHandlers['Yes']?.();
    mockModalClickHandlers['No']?.();

    const result = await promise;
    expect(result).toBe(true);
  });
});

describe('alertAsync', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    mockModalClickHandlers = {};
    mockOnClose = null;
  });

  it('resolves when OK button is clicked', async () => {
    const promise = alertAsync({
      title: 'Info',
      message: 'Something happened',
      okLabel: 'OK',
    });

    mockModalClickHandlers['OK']?.();

    await expect(promise).resolves.toBeUndefined();
  });

  it('resolves when modal is closed via onClose', async () => {
    const promise = alertAsync({
      title: 'Info',
      message: 'Something happened',
      okLabel: 'OK',
    });

    mockOnClose?.();

    await expect(promise).resolves.toBeUndefined();
  });

  it('only settles once', async () => {
    const promise = alertAsync({
      title: 'Info',
      message: 'Done',
      okLabel: 'OK',
    });

    mockModalClickHandlers['OK']?.();
    mockOnClose?.();

    await expect(promise).resolves.toBeUndefined();
  });
});
