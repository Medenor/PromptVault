/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type {
  FormGroupProps,
  SelectProps,
  CheckboxProps,
  RadioGroupProps,
  InputProps,
} from './types';
import { createInput } from './input';

/**
 * Creates a form group with label, input, and validation messages
 * @param child - The input element to wrap
 * @param props - Form group properties
 * @returns HTMLDivElement containing labeled form field
 */
export function createFormGroup(child: HTMLElement, props: FormGroupProps): HTMLDivElement {
  const group = document.createElement('div');
  group.className = `flex flex-col gap-1 ${props?.className || ''}`.trim();

  const fieldId =
    props.htmlFor ||
    // If the caller passed an actual form control, we can infer the id for help/error associations.
    ((child instanceof HTMLInputElement ||
      child instanceof HTMLTextAreaElement ||
      child instanceof HTMLSelectElement) &&
    child.id
      ? child.id
      : '') ||
    props.id ||
    'field';

  if (props.label) {
    const label = document.createElement('label');
    label.className = 'font-medium text-gray-900 text-sm';
    if (props.htmlFor) {
      label.htmlFor = props.htmlFor;
    } else if (
      (child instanceof HTMLInputElement ||
        child instanceof HTMLTextAreaElement ||
        child instanceof HTMLSelectElement) &&
      child.id
    ) {
      // Reasonable default: if a form control id exists, associate label to it.
      label.htmlFor = child.id;
    }

    // Label text
    const labelText = document.createTextNode(props.label);
    label.appendChild(labelText);

    // Required indicator
    if (props.required) {
      const required = document.createElement('span');
      required.textContent = ' *';
      required.className = 'text-red-500';
      label.appendChild(required);
    }

    group.appendChild(label);
  }

  group.appendChild(child);

  // Link help/error text to the form control via aria-describedby.
  // This keeps screen reader users in-sync with inline help and validation messages.
  const control =
    props.htmlFor && group.querySelector<HTMLElement>(`#${props.htmlFor}`)
      ? group.querySelector<HTMLElement>(`#${props.htmlFor}`)!
      : child instanceof HTMLInputElement ||
          child instanceof HTMLTextAreaElement ||
          child instanceof HTMLSelectElement
        ? child
        : null;

  const mergeDescribedBy = (el: HTMLElement, ids: string[]) => {
    const existing =
      el
        .getAttribute('aria-describedby')
        ?.split(/\s+/)
        .map((s) => s.trim())
        .filter(Boolean) ?? [];
    const next = Array.from(new Set([...existing, ...ids.filter(Boolean)]));
    if (next.length) el.setAttribute('aria-describedby', next.join(' '));
  };

  // Error message (takes precedence over help text)
  if (props.error) {
    const errorId = `${fieldId}-error`;
    const error = document.createElement('p');
    error.id = errorId;
    error.textContent = props.error;
    error.className = 'text-sm text-red-500 mt-1';
    error.setAttribute('role', 'alert');
    group.appendChild(error);
    if (control) mergeDescribedBy(control, [errorId]);
  } else if (props.helpText) {
    // Help text only shown if no error
    const helpId = `${fieldId}-help`;
    const help = document.createElement('p');
    help.id = helpId;
    help.textContent = props.helpText;
    help.className = 'text-sm text-gray-500 mt-1';
    group.appendChild(help);
    if (control) mergeDescribedBy(control, [helpId]);
  }

  if (props.id) group.id = props.id;

  return group;
}

/**
 * Creates a labeled input field (convenience wrapper)
 * @param label - Label text
 * @param inputProps - Input properties
 * @param formProps - Form group properties
 * @returns Form group with input
 */
export function createLabeledInput(
  label: string,
  inputProps?: InputProps,
  formProps?: Omit<FormGroupProps, 'label'>
): HTMLDivElement {
  const inputId = inputProps?.id || `input-${Math.random().toString(36).substr(2, 9)}`;
  const input = createInput({ ...inputProps, id: inputId });

  return createFormGroup(input, {
    label,
    htmlFor: inputId,
    ...formProps,
  });
}

/**
 * Creates a select dropdown with Tailwind styling
 * @param props - Select properties
 * @returns Styled select element
 */
export function createSelectInput(
  options: Array<{ label: string; value: string; disabled?: boolean }>,
  props?: SelectProps
): HTMLSelectElement {
  const select = document.createElement('select');

  // Tailwind styling matching input design
  const baseClasses =
    'w-full px-3 py-2 rounded-md transition-all duration-200 focus:outline-none focus:ring-2';
  const stateClasses = props?.error
    ? 'bg-red-50 border-2 border-red-500 focus:border-red-600 focus:ring-red-500'
    : 'bg-gray-100 border-2 border-gray-100 focus:border-blue-500 focus:bg-white focus:ring-blue-500';
  const disabledClasses = props?.disabled ? 'opacity-50 cursor-not-allowed' : '';

  select.className =
    `${baseClasses} ${stateClasses} ${disabledClasses} ${props?.className || ''}`.trim();

  if (props?.name) select.name = props.name;
  if (props?.disabled) select.disabled = true;
  if (props?.required) select.required = true;
  if (props?.id) select.id = props.id;
  if (props?.ariaLabel) select.setAttribute('aria-label', props.ariaLabel);
  if (props?.onChange) select.addEventListener('change', props.onChange);

  // Error state ARIA
  if (props?.error) {
    select.setAttribute('aria-invalid', 'true');
    if (props.errorMessage) {
      select.setAttribute('aria-describedby', `${props.id || 'select'}-error`);
    }
  }

  options.forEach((opt) => {
    const option = document.createElement('option');
    option.value = opt.value;
    option.textContent = opt.label;
    if (opt.disabled) option.disabled = true;
    if (props?.value === opt.value) option.selected = true;
    select.appendChild(option);
  });

  return select;
}

/**
 * Creates a checkbox with label
 * @param label - Checkbox label
 * @param props - Checkbox properties
 * @returns Div containing checkbox and label
 */
export function createCheckbox(label: string, props?: CheckboxProps): HTMLDivElement {
  const wrapper = document.createElement('div');
  wrapper.className = `flex items-center gap-2 ${props?.className || ''}`.trim();

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.id = props?.id || `checkbox-${Math.random().toString(36).substr(2, 9)}`;
  checkbox.className =
    'w-4 h-4 text-blue-500 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 transition-all duration-200';

  if (props?.checked) checkbox.checked = true;
  if (props?.disabled) {
    checkbox.disabled = true;
    checkbox.classList.add('opacity-50', 'cursor-not-allowed');
  }
  if (props?.required) checkbox.required = true;
  if (props?.name) checkbox.name = props.name;
  if (props?.value) checkbox.value = props.value;
  if (props?.ariaLabel) checkbox.setAttribute('aria-label', props.ariaLabel);
  if (props?.onChange) checkbox.addEventListener('change', props.onChange);

  const labelElement = document.createElement('label');
  labelElement.htmlFor = checkbox.id;
  labelElement.textContent = label;
  labelElement.className = 'text-sm font-medium text-gray-900 cursor-pointer select-none';

  if (props?.disabled) {
    labelElement.classList.add('opacity-50', 'cursor-not-allowed');
  }

  wrapper.appendChild(checkbox);
  wrapper.appendChild(labelElement);

  return wrapper;
}

/**
 * Creates a radio button group
 * @param label - Group label
 * @param options - Radio button options
 * @param props - Radio group properties
 * @returns Fieldset containing radio buttons
 */
export function createRadioGroup(
  label: string,
  options: Array<{ label: string; value: string; disabled?: boolean }>,
  props?: RadioGroupProps
): HTMLFieldSetElement {
  const fieldset = document.createElement('fieldset');
  fieldset.className = `border-0 p-0 ${props?.className || ''}`.trim();

  if (props?.id) fieldset.id = props.id;
  if (props?.disabled) fieldset.disabled = true;

  const legend = document.createElement('legend');
  legend.textContent = label;
  legend.className = 'font-medium text-gray-900 text-sm mb-2';

  if (props?.required) {
    const required = document.createElement('span');
    required.textContent = ' *';
    required.className = 'text-red-500';
    legend.appendChild(required);
  }

  fieldset.appendChild(legend);

  const radioContainer = document.createElement('div');
  radioContainer.className = 'flex flex-col gap-2';

  options.forEach((opt, index) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'flex items-center gap-2';

    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = props?.name || 'radio-group';
    radio.value = opt.value;
    radio.id = `${props?.name || 'radio'}-${index}`;
    radio.className =
      'w-4 h-4 text-blue-500 bg-gray-100 border-gray-300 focus:ring-blue-500 focus:ring-2 transition-all duration-200';

    if (props?.value === opt.value) radio.checked = true;
    if (opt.disabled || props?.disabled) {
      radio.disabled = true;
      radio.classList.add('opacity-50', 'cursor-not-allowed');
    }
    if (props?.required) radio.required = true;
    if (props?.onChange) radio.addEventListener('change', props.onChange);

    const labelElement = document.createElement('label');
    labelElement.htmlFor = radio.id;
    labelElement.textContent = opt.label;
    labelElement.className = 'text-sm font-medium text-gray-900 cursor-pointer select-none';

    if (opt.disabled || props?.disabled) {
      labelElement.classList.add('opacity-50', 'cursor-not-allowed');
    }

    wrapper.appendChild(radio);
    wrapper.appendChild(labelElement);
    radioContainer.appendChild(wrapper);
  });

  fieldset.appendChild(radioContainer);

  return fieldset;
}
