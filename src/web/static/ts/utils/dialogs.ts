/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Non-blocking dialog helpers.
 *
 * We avoid `window.confirm` / `window.alert` because they block the UI thread
 * and are inconsistent for assistive tech. These helpers use our modal component
 * and return Promises.
 */

import { createModal } from '@/components/modal';

export async function confirmAsync(options: {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
}): Promise<boolean> {
  return await new Promise<boolean>((resolve) => {
    let settled = false;
    const settle = (value: boolean) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };

    const modal = createModal({
      title: options.title,
      content: `<p class="text-sm text-gray-700">${options.message}</p>`,
      size: 'sm',
      actions: [
        {
          label: options.cancelLabel,
          variant: 'secondary',
          onClick: () => {
            modal.close();
            modal.element.remove();
            settle(false);
          },
        },
        {
          label: options.confirmLabel,
          variant: 'primary',
          onClick: () => {
            modal.close();
            modal.element.remove();
            settle(true);
          },
        },
      ],
      onClose: () => {
        // If the user closes with ESC/backdrop, treat as cancellation.
        modal.element.remove();
        settle(false);
      },
    });

    document.body.appendChild(modal.element);
    modal.open();
  });
}

export async function alertAsync(options: {
  title: string;
  message: string;
  okLabel: string;
}): Promise<void> {
  await new Promise<void>((resolve) => {
    let settled = false;
    const settle = () => {
      if (settled) return;
      settled = true;
      resolve();
    };

    const modal = createModal({
      title: options.title,
      content: `<p class="text-sm text-gray-700">${options.message}</p>`,
      size: 'sm',
      actions: [
        {
          label: options.okLabel,
          variant: 'primary',
          onClick: () => {
            modal.close();
            modal.element.remove();
            settle();
          },
        },
      ],
      onClose: () => {
        modal.element.remove();
        settle();
      },
    });

    document.body.appendChild(modal.element);
    modal.open();
  });
}
