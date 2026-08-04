/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => key),
    language: 'en',
  },
}));

const announceMock = vi.fn();
vi.mock('@/utils/a11y', () => ({
  announce: (...args: unknown[]) => announceMock(...args),
}));

import {
  addFieldError,
  clearLiveFieldError,
  getLiveValidationState,
  renderErrorSummary,
  resetErrorSummary,
  resetFieldError,
  setLiveFieldError,
  validateExportForm,
  validateImportForm,
} from '../validation';

function setBody(html: string): void {
  document.body.innerHTML = html;
}

beforeEach(() => {
  document.body.innerHTML = '';
  announceMock.mockClear();
});

describe('validateExportForm', () => {
  beforeEach(() => {
    setBody(
      '<input id="export-filename" /><span id="export-filename-error"></span><div id="export-error-summary"></div>'
    );
  });

  it('requires a non-empty filename', () => {
    const errors = validateExportForm('   ');
    expect(errors).toHaveLength(1);
    expect(errors[0]?.inputId).toBe('export-filename');
  });

  it('rejects filenames with disallowed characters', () => {
    const errors = validateExportForm('bad name!.csv');
    expect(errors).toHaveLength(1);
  });

  it('accepts a valid filename', () => {
    const errors = validateExportForm('my-export_1.csv');
    expect(errors).toHaveLength(0);
  });
});

describe('validateImportForm', () => {
  beforeEach(() => {
    setBody(
      '<input id="import-file" /><span id="import-file-error"></span><div id="import-error-summary"></div>'
    );
  });

  it('requires a file', () => {
    const errors = validateImportForm(undefined);
    expect(errors).toHaveLength(1);
    expect(errors[0]?.inputId).toBe('import-file');
  });

  it('accepts a selected file', () => {
    const file = new File(['content'], 'data.csv');
    const errors = validateImportForm(file);
    expect(errors).toHaveLength(0);
  });
});

describe('live field error helpers', () => {
  let fieldId: string;
  let errorId: string;
  let counter = 0;

  beforeEach(() => {
    counter += 1;
    fieldId = `field-a-${counter}`;
    errorId = `field-a-${counter}-error`;
    setBody(`<input id="${fieldId}" /><span id="${errorId}"></span>`);
  });

  it('sets aria-invalid and announces once on first error', () => {
    setLiveFieldError(fieldId, errorId, 'Bad value');
    const input = document.getElementById(fieldId);
    const error = document.getElementById(errorId);
    expect(input?.getAttribute('aria-invalid')).toBe('true');
    expect(error?.textContent).toBe('Bad value');
    expect(getLiveValidationState(fieldId)).toBe(true);
    expect(announceMock).toHaveBeenCalledTimes(1);
  });

  it('does not re-announce on repeated errors', () => {
    setLiveFieldError(fieldId, errorId, 'Bad value');
    setLiveFieldError(fieldId, errorId, 'Still bad');
    expect(announceMock).toHaveBeenCalledTimes(1);
  });

  it('clears error state and announces validity restored', () => {
    setLiveFieldError(fieldId, errorId, 'Bad value');
    announceMock.mockClear();
    clearLiveFieldError(fieldId, errorId);
    const input = document.getElementById(fieldId);
    expect(input?.getAttribute('aria-invalid')).toBe('false');
    expect(getLiveValidationState(fieldId)).toBe(false);
    expect(announceMock).toHaveBeenCalledTimes(1);
  });
});

describe('resetFieldError', () => {
  it('clears aria-invalid and error text', () => {
    setBody('<input id="field-b" aria-invalid="true" /><span id="field-b-error">oops</span>');
    resetFieldError('field-b', 'field-b-error');
    expect(document.getElementById('field-b')?.getAttribute('aria-invalid')).toBe('false');
    expect(document.getElementById('field-b-error')?.textContent).toBe('');
  });
});

describe('addFieldError / renderErrorSummary', () => {
  it('accumulates aria-describedby ids without duplicates', () => {
    setBody('<input id="field-c" /><span id="field-c-error"></span>');
    const errors: { inputId: string; message: string }[] = [];
    addFieldError(errors, 'field-c', 'field-c-error', 'First');
    addFieldError(errors, 'field-c', 'field-c-error', 'Second');
    expect(errors).toHaveLength(2);
    expect(document.getElementById('field-c')?.getAttribute('aria-describedby')).toBe(
      'field-c-error'
    );
  });

  it('renders an error summary list and focuses the first input', () => {
    setBody('<input id="field-d" /><div id="summary"></div>');
    const errors = [{ inputId: 'field-d', message: 'Required' }];
    renderErrorSummary('summary', errors);
    const summary = document.getElementById('summary') as HTMLElement;
    expect(summary.style.display).toBe('block');
    expect(summary.querySelectorAll('li')).toHaveLength(1);
  });

  it('does nothing when there are no errors', () => {
    setBody('<div id="summary"></div>');
    renderErrorSummary('summary', []);
    expect(document.getElementById('summary')?.textContent).toBe('');
  });
});

describe('resetErrorSummary', () => {
  it('clears summary content and hides it', () => {
    setBody('<div id="summary">stuff</div>');
    resetErrorSummary('summary');
    const summary = document.getElementById('summary') as HTMLElement;
    expect(summary.textContent).toBe('');
    expect(summary.style.display).toBe('none');
  });
});
