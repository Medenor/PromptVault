/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { FormGroupProps, SelectProps } from './types';

/**
 * Form Component Factories
 * Full implementation in Phase 2
 */

export function createFormGroup(child: HTMLElement, props: FormGroupProps): HTMLDivElement {
  const group = document.createElement('div');
  group.className = `form-group ${props?.className || ''}`.trim();

  if (props.label) {
    const label = document.createElement('label');
    label.textContent = props.label;
    label.className = 'block text-sm font-medium text-foreground mb-1';
    if (props.htmlFor) label.htmlFor = props.htmlFor;
    if (props.required) {
      const required = document.createElement('span');
      required.textContent = ' *';
      required.className = 'text-red-500';
      label.appendChild(required);
    }
    group.appendChild(label);
  }

  group.appendChild(child);

  if (props.error) {
    const error = document.createElement('p');
    error.textContent = props.error;
    error.className = 'text-sm text-red-500 mt-1';
    group.appendChild(error);
  }

  if (props.help) {
    const help = document.createElement('p');
    help.textContent = props.help;
    help.className = 'text-sm text-gray-500 mt-1';
    group.appendChild(help);
  }

  if (props.id) group.id = props.id;

  return group;
}

export function createSelect(props: SelectProps): HTMLSelectElement {
  const select = document.createElement('select');

  // Basic Tailwind styling as placeholder
  const baseClasses = 'w-full px-3 py-2 border border-border rounded-md text-foreground bg-white';
  const focusClasses = 'focus:ring-2 focus:ring-primary focus:border-primary';

  select.className = `${baseClasses} ${focusClasses} ${props?.className || ''}`.trim();

  if (props.name) select.name = props.name;
  if (props.disabled) select.disabled = true;
  if (props.required) select.required = true;
  if (props.id) select.id = props.id;
  if (props.ariaLabel) select.setAttribute('aria-label', props.ariaLabel);
  if (props.onChange) select.addEventListener('change', props.onChange);

  props.options.forEach((opt) => {
    const option = document.createElement('option');
    option.value = opt.value;
    option.textContent = opt.label;
    if (opt.disabled) option.disabled = true;
    if (props.value === opt.value) option.selected = true;
    select.appendChild(option);
  });

  return select;
}
