/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Main app - TypeScript migration in progress
 */

import { initI18n, updateStaticTranslations } from '@/utils/i18n';
import { reportError } from '@/telemetry';

function initializeApp(): void {
  updateStaticTranslations();
}

initI18n(() => {
  try {
    initializeApp();
  } catch (error) {
    reportError('app', 'initialize', error);
  }
});
