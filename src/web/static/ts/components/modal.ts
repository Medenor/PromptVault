/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { ModalProps } from './types';

/**
 * Modal Component Factory
 * Full implementation in Phase 2
 */

export function createModal(content: HTMLElement | string, props?: ModalProps): HTMLDivElement {
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 hidden';

  const modalContent = document.createElement('div');
  const baseClasses = 'bg-white rounded-lg p-6';
  const sizeClasses = getSizeClasses(props?.size || 'md');

  modalContent.className = `${baseClasses} ${sizeClasses} ${props?.className || ''}`.trim();

  if (props?.title) {
    const header = document.createElement('div');
    header.className = 'flex items-center justify-between mb-4';

    const title = document.createElement('h2');
    title.textContent = props.title;
    title.className = 'text-2xl font-semibold text-foreground';
    header.appendChild(title);

    if (props.showClose !== false) {
      const closeBtn = document.createElement('button');
      closeBtn.innerHTML = '&times;';
      closeBtn.className = 'text-gray-400 hover:text-gray-600 text-3xl font-normal';
      closeBtn.addEventListener('click', () => closeModal(modal, props?.onClose));
      header.appendChild(closeBtn);
    }

    modalContent.appendChild(header);
  }

  const body = document.createElement('div');
  if (typeof content === 'string') {
    body.innerHTML = content;
  } else {
    body.appendChild(content);
  }
  modalContent.appendChild(body);

  modal.appendChild(modalContent);

  if (props?.closeOnBackdrop !== false) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal(modal, props?.onClose);
    });
  }

  if (props?.closeOnEscape !== false) {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
        closeModal(modal, props?.onClose);
      }
    });
  }

  if (props?.id) modal.id = props.id;

  return modal;
}

export function openModal(modal: HTMLDivElement): void {
  modal.classList.remove('hidden');
}

export function closeModal(modal: HTMLDivElement, onClose?: () => void): void {
  modal.classList.add('hidden');
  if (onClose) onClose();
}

function getSizeClasses(size: string): string {
  const sizes: Record<string, string> = {
    sm: 'max-w-sm w-full',
    md: 'max-w-md w-full',
    lg: 'max-w-lg w-full',
    xl: 'max-w-xl w-full',
    full: 'max-w-full w-full h-full',
  };
  return sizes[size] ?? sizes['md'] ?? '';
}
