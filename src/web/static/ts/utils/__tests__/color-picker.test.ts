/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ColorPicker, PRESET_COLORS, initializeColorPicker } from '../color-picker';

function setupDOM(initialColor = '#3B82F6') {
  document.body.innerHTML = `
    <div id="color-container"></div>
    <input type="text" id="color-input" value="${initialColor}" />
    <input type="color" id="color-picker-native" value="${initialColor}" />
  `;
}

describe('PRESET_COLORS', () => {
  it('contains at least one color', () => {
    expect(PRESET_COLORS.length).toBeGreaterThan(0);
    expect(PRESET_COLORS[0]).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });
});

describe('ColorPicker', () => {
  beforeEach(() => {
    setupDOM();
  });

  it('throws when required elements are missing', () => {
    document.body.innerHTML = '';
    expect(
      () =>
        new ColorPicker({
          containerId: 'missing',
          colorInputId: 'missing-input',
          colorPickerId: 'missing-picker',
        })
    ).toThrow('Required color picker elements not found');
  });

  it('initializes with provided color', () => {
    const picker = new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
      initialColor: '#EF4444',
    });

    expect(picker.getColor()).toBe('#EF4444');
  });

  it('defaults to #3B82F6 when no initialColor provided', () => {
    const picker = new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
    });

    expect(picker.getColor()).toBe('#3B82F6');
  });

  it('calls onChange when color is set via preset click', () => {
    const onChange = vi.fn();
    new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
      onChange,
    });

    const presetBtn = document.querySelector('.preset-color') as HTMLButtonElement;
    expect(presetBtn).not.toBeNull();
    presetBtn.click();

    expect(onChange).toHaveBeenCalled();
  });

  it('updates color from hex input with valid hex', () => {
    const onChange = vi.fn();
    new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
      onChange,
    });

    const hexInput = document.querySelector('input[type="text"]') as HTMLInputElement;
    hexInput.value = '#22C55E';
    hexInput.dispatchEvent(new Event('input'));

    expect(onChange).toHaveBeenCalledWith('#22C55E');
  });

  it('ignores invalid hex from hex input', () => {
    const onChange = vi.fn();
    new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
      onChange,
    });

    onChange.mockClear();

    const hexInput = document.querySelector('input[type="text"]') as HTMLInputElement;
    hexInput.value = 'notacolor';
    hexInput.dispatchEvent(new Event('input'));

    expect(onChange).not.toHaveBeenCalled();
  });

  it('resets hex input to current color on blur if invalid', () => {
    const picker = new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
      initialColor: '#EF4444',
    });

    const hexInput = document.querySelector('input[type="text"]') as HTMLInputElement;
    hexInput.value = 'badvalue';
    hexInput.dispatchEvent(new Event('blur'));

    expect(hexInput.value).toBe('#EF4444');
  });

  it('updates color from native color picker input', () => {
    const onChange = vi.fn();
    new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
      onChange,
    });

    const nativePicker = document.getElementById('color-picker-native') as HTMLInputElement;
    nativePicker.value = '#6366F1';
    nativePicker.dispatchEvent(new Event('input'));

    expect(onChange).toHaveBeenCalledWith('#6366F1');
  });

  it('getColor returns current color', () => {
    const picker = new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
      initialColor: '#A855F7',
    });

    expect(picker.getColor()).toBe('#A855F7');
  });

  it('destroy clears container', () => {
    const picker = new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
    });

    picker.destroy();
    const container = document.getElementById('color-container') as HTMLElement;
    expect(container.innerHTML).toBe('');
  });

  it('preset keyboard navigation: ArrowRight moves focus', () => {
    new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
    });

    const presets = document.querySelectorAll('.preset-color') as NodeListOf<HTMLButtonElement>;
    const firstBtn = presets[0] as HTMLButtonElement;
    const secondBtn = presets[1] as HTMLButtonElement;
    const focusSpy = vi.spyOn(secondBtn, 'focus');

    const event = new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true });
    Object.defineProperty(event, 'target', { value: firstBtn });
    firstBtn.dispatchEvent(event);

    expect(focusSpy).toHaveBeenCalled();
  });

  it('preset keyboard navigation: ArrowLeft moves focus', () => {
    new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
    });

    const presets = document.querySelectorAll('.preset-color') as NodeListOf<HTMLButtonElement>;
    const firstBtn = presets[0] as HTMLButtonElement;
    const lastBtn = presets[presets.length - 1] as HTMLButtonElement;
    const focusSpy = vi.spyOn(lastBtn, 'focus');

    const event = new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true });
    Object.defineProperty(event, 'target', { value: firstBtn });
    firstBtn.dispatchEvent(event);

    expect(focusSpy).toHaveBeenCalled();
  });

  it('preset keyboard Enter selects color', () => {
    const onChange = vi.fn();
    new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
      onChange,
    });

    const firstBtn = document.querySelector('.preset-color') as HTMLButtonElement;
    const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    Object.defineProperty(event, 'target', { value: firstBtn });
    firstBtn.dispatchEvent(event);

    expect(onChange).toHaveBeenCalled();
  });

  it('preset keyboard Escape blurs', () => {
    new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
    });

    const firstBtn = document.querySelector('.preset-color') as HTMLButtonElement;
    const blurSpy = vi.spyOn(firstBtn, 'blur');

    const event = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
    Object.defineProperty(event, 'target', { value: firstBtn });
    firstBtn.dispatchEvent(event);

    expect(blurSpy).toHaveBeenCalled();
  });

  it('preset keyboard ArrowDown moves 5 forward', () => {
    new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
    });

    const presets = document.querySelectorAll('.preset-color') as NodeListOf<HTMLButtonElement>;
    const firstBtn = presets[0] as HTMLButtonElement;
    const fifthBtn = presets[5] as HTMLButtonElement;
    const focusSpy = vi.spyOn(fifthBtn, 'focus');

    const event = new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true });
    Object.defineProperty(event, 'target', { value: firstBtn });
    firstBtn.dispatchEvent(event);

    expect(focusSpy).toHaveBeenCalled();
  });

  it('preset keyboard ArrowUp moves 5 backward (clamped to 0)', () => {
    new ColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
    });

    const presets = document.querySelectorAll('.preset-color') as NodeListOf<HTMLButtonElement>;
    const firstBtn = presets[0] as HTMLButtonElement;
    const focusSpy = vi.spyOn(firstBtn, 'focus');

    const event = new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true });
    Object.defineProperty(event, 'target', { value: firstBtn });
    firstBtn.dispatchEvent(event);

    // ArrowUp from index 0 stays at 0, no focus call since index unchanged
    expect(focusSpy).not.toHaveBeenCalled();
  });
});

describe('initializeColorPicker', () => {
  it('returns a ColorPicker instance', () => {
    setupDOM('#FF0000');
    const picker = initializeColorPicker({
      containerId: 'color-container',
      colorInputId: 'color-input',
      colorPickerId: 'color-picker-native',
      initialColor: '#FF0000',
    });
    expect(picker).toBeInstanceOf(ColorPicker);
    expect(picker.getColor()).toBe('#FF0000');
  });
});
