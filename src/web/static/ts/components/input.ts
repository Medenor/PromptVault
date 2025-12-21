/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { InputProps, TextareaProps, FileUploadProps } from './types';

/**
 * Creates a styled input element
 * @param props - Input properties
 * @returns HTMLInputElement with Tailwind styling
 */
export function createInput(props: InputProps = {}): HTMLInputElement {
  const input = document.createElement('input');
  input.type = props.type || 'text';

  // Base classes following design system
  const baseClasses = 'w-full px-3 py-2 rounded-md transition-all duration-200 focus:outline-none focus:ring-2';

  // Default state: gray background, border on focus
  let stateClasses = 'bg-gray-100 border-2 border-gray-100 focus:border-blue-500 focus:bg-white focus:ring-blue-500';

  // Error state: red border and background
  if (props.error) {
    stateClasses = 'bg-red-50 border-2 border-red-500 focus:border-red-600 focus:ring-red-500';
  }

  // Success state: green border and background
  if (props.success) {
    stateClasses = 'bg-green-50 border-2 border-green-500 focus:border-green-600 focus:ring-green-500';
  }

  // Disabled state
  const disabledClasses = props.disabled ? 'opacity-50 cursor-not-allowed' : '';

  // Readonly state
  const readonlyClasses = props.readonly ? 'bg-gray-50 cursor-default' : '';

  // Build class list
  let classList = `${baseClasses} ${stateClasses} ${disabledClasses} ${readonlyClasses}`;

  if (props.className) {
    classList += ` ${props.className}`;
  }

  input.className = classList.trim();

  // Set attributes
  if (props.placeholder) input.placeholder = props.placeholder;
  if (props.value !== undefined) input.value = props.value;
  if (props.name) input.name = props.name;
  if (props.disabled) input.disabled = true;
  if (props.readonly) input.readOnly = true;
  if (props.required) input.required = true;
  if (props.pattern) input.pattern = props.pattern;
  if (props.minLength !== undefined) input.minLength = props.minLength;
  if (props.maxLength !== undefined) input.maxLength = props.maxLength;
  if (props.autocomplete) input.setAttribute('autocomplete', props.autocomplete);
  if (props.id) input.id = props.id;
  if (props.ariaLabel) input.setAttribute('aria-label', props.ariaLabel);

  // Error state ARIA
  if (props.error) {
    input.setAttribute('aria-invalid', 'true');
    if (props.errorMessage) {
      input.setAttribute('aria-describedby', `${props.id || 'input'}-error`);
    }
  }

  // Event listeners
  if (props.onChange) input.addEventListener('change', props.onChange);
  if (props.onInput) input.addEventListener('input', props.onInput);
  if (props.onBlur) input.addEventListener('blur', props.onBlur);
  if (props.onFocus) input.addEventListener('focus', props.onFocus);

  return input;
}

/**
 * Creates a styled textarea element
 * @param props - Textarea properties
 * @returns HTMLTextAreaElement with Tailwind styling
 */
export function createTextarea(props: TextareaProps = {}): HTMLTextAreaElement {
  const textarea = document.createElement('textarea');

  // Base classes following design system
  const baseClasses = 'w-full px-3 py-2 rounded-md transition-all duration-200 focus:outline-none focus:ring-2 resize-vertical';

  // Default state
  let stateClasses = 'bg-gray-100 border-2 border-gray-100 focus:border-blue-500 focus:bg-white focus:ring-blue-500';

  // Error state
  if (props.error) {
    stateClasses = 'bg-red-50 border-2 border-red-500 focus:border-red-600 focus:ring-red-500';
  }

  // Success state
  if (props.success) {
    stateClasses = 'bg-green-50 border-2 border-green-500 focus:border-green-600 focus:ring-green-500';
  }

  // Disabled state
  const disabledClasses = props.disabled ? 'opacity-50 cursor-not-allowed' : '';

  // Readonly state
  const readonlyClasses = props.readonly ? 'bg-gray-50 cursor-default' : '';

  // Build class list
  let classList = `${baseClasses} ${stateClasses} ${disabledClasses} ${readonlyClasses}`;

  if (props.className) {
    classList += ` ${props.className}`;
  }

  textarea.className = classList.trim();

  // Set attributes
  if (props.placeholder) textarea.placeholder = props.placeholder;
  if (props.value !== undefined) textarea.value = props.value;
  if (props.name) textarea.name = props.name;
  if (props.rows) textarea.rows = props.rows;
  if (props.cols) textarea.cols = props.cols;
  if (props.disabled) textarea.disabled = true;
  if (props.readonly) textarea.readOnly = true;
  if (props.required) textarea.required = true;
  if (props.minLength !== undefined) textarea.minLength = props.minLength;
  if (props.maxLength !== undefined) textarea.maxLength = props.maxLength;
  if (props.id) textarea.id = props.id;
  if (props.ariaLabel) textarea.setAttribute('aria-label', props.ariaLabel);

  // Error state ARIA
  if (props.error) {
    textarea.setAttribute('aria-invalid', 'true');
    if (props.errorMessage) {
      textarea.setAttribute('aria-describedby', `${props.id || 'textarea'}-error`);
    }
  }

  // Event listeners
  if (props.onChange) textarea.addEventListener('change', props.onChange);
  if (props.onInput) textarea.addEventListener('input', props.onInput);
  if (props.onBlur) textarea.addEventListener('blur', props.onBlur);
  if (props.onFocus) textarea.addEventListener('focus', props.onFocus);

  return textarea;
}

/**
 * Creates an email input with validation
 * @param props - Input properties
 * @returns Email input element
 */
export function createEmailInput(props: InputProps = {}): HTMLInputElement {
  return createInput({
    ...props,
    type: 'email',
    autocomplete: props.autocomplete || 'email',
  });
}

/**
 * Creates a password input
 * @param props - Input properties
 * @returns Password input element
 */
export function createPasswordInput(props: InputProps = {}): HTMLInputElement {
  return createInput({
    ...props,
    type: 'password',
    autocomplete: props.autocomplete || 'current-password',
  });
}

/**
 * Creates a search input
 * @param props - Input properties
 * @returns Search input element
 */
export function createSearchInput(props: InputProps = {}): HTMLInputElement {
  return createInput({
    ...props,
    type: 'search',
    placeholder: props.placeholder || 'Search...',
  });
}

/**
 * Creates a number input
 * @param props - Input properties
 * @returns Number input element
 */
export function createNumberInput(props: InputProps = {}): HTMLInputElement {
  return createInput({
    ...props,
    type: 'number',
  });
}

/**
 * Creates a date input
 * @param props - Input properties
 * @returns Date input element
 */
export function createDateInput(props: InputProps = {}): HTMLInputElement {
  return createInput({
    ...props,
    type: 'date',
  });
}

/**
 * Creates a file input with custom styling
 * @param props - File upload properties
 * @returns Styled file input wrapper
 */
export function createFileInput(props: FileUploadProps = {}): HTMLDivElement {
  const wrapper = document.createElement('div');
  wrapper.className = `relative ${props.className || ''}`.trim();

  const input = document.createElement('input');
  input.type = 'file';
  input.className = 'hidden';

  if (props.accept) input.accept = props.accept;
  if (props.multiple) input.multiple = true;
  if (props.disabled) input.disabled = true;
  if (props.required) input.required = true;
  if (props.name) input.name = props.name;
  if (props.id) input.id = props.id;

  // Create visible button
  const button = document.createElement('button');
  button.type = 'button';
  button.className =
    'w-full px-4 py-2 bg-gray-100 border-2 border-gray-300 border-dashed rounded-md text-gray-700 hover:bg-gray-200 hover:border-gray-400 transition-all duration-200 cursor-pointer';
  button.textContent = 'Choose File';

  if (props.disabled) {
    button.disabled = true;
    button.classList.add('opacity-50', 'cursor-not-allowed');
  }

  // File name display
  const fileDisplay = document.createElement('span');
  fileDisplay.className = 'ml-2 text-sm text-gray-600';

  button.addEventListener('click', () => input.click());

  input.addEventListener('change', (e) => {
    const files = (e.target as HTMLInputElement).files;
    if (files && files.length > 0) {
      const fileNames = Array.from(files)
        .map((f) => f.name)
        .join(', ');
      fileDisplay.textContent = fileNames;
    } else {
      fileDisplay.textContent = '';
    }

    if (props.onChange) props.onChange(e);
    if (props.onFilesSelected) props.onFilesSelected(files);
  });

  wrapper.appendChild(input);
  wrapper.appendChild(button);
  wrapper.appendChild(fileDisplay);

  return wrapper;
}
