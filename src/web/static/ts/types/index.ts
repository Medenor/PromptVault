/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

export * from './api/enums';
export * from './api/requests';
export * from './api/responses';
export * from './state/app-state';
export * from './validation';

export interface FrontendLogger {
  reportError: (
    component: string,
    action: string,
    error: unknown,
    metadata?: Record<string, unknown>,
    severity?: 'error' | 'warning' | 'info'
  ) => void;
  enable: () => void;
  disable: () => void;
  isEnabled: () => boolean;
}
