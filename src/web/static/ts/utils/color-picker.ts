/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

export const PRESET_COLORS = [
  '#EF4444', // red
  '#F97316', // orange
  '#FBBF24', // yellow
  '#22C55E', // green
  '#14B8A6', // teal
  '#3B82F6', // blue
  '#6366F1', // indigo
  '#A855F7', // purple
  '#EC4899', // pink
  '#6B7280', // gray
  '#1F2937', // dark gray
];

export interface ColorPickerConfig {
  containerId: string;
  colorInputId: string;
  colorPickerId: string;
  initialColor?: string;
  onChange?: (color: string) => void;
}

export class ColorPicker {
  private container: HTMLElement;
  private colorInput: HTMLInputElement;
  private colorPicker: HTMLInputElement;
  private hexInput: HTMLInputElement | null = null;
  private previewBox: HTMLElement | null = null;
  private presetsContainer: HTMLElement | null = null;
  private config: ColorPickerConfig;
  private currentColor: string;
  private selectedPresetButton: HTMLButtonElement | null = null;

  constructor(config: ColorPickerConfig) {
    this.config = config;
    this.currentColor = config.initialColor || '#3B82F6';

    const container = document.getElementById(config.containerId);
    const colorInput = document.getElementById(config.colorInputId) as HTMLInputElement;
    const colorPicker = document.getElementById(config.colorPickerId) as HTMLInputElement;

    if (!container || !colorInput || !colorPicker) {
      throw new Error('Required color picker elements not found');
    }

    this.container = container;
    this.colorInput = colorInput;
    this.colorPicker = colorPicker;

    this.initialize();
  }

  private initialize(): void {
    // Build enhanced UI
    this.buildEnhancedUI();

    // Set up event listeners
    this.setupEventListeners();

    // Set initial color
    this.setColor(this.currentColor);
  }

  private buildEnhancedUI(): void {
    // Clear container
    this.container.innerHTML = '';

    // Create wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'color-picker-container space-y-2';

    // Create preview and hex input row
    const previewRow = document.createElement('div');
    previewRow.className = 'flex gap-2 items-center';

    // Preview box
    this.previewBox = document.createElement('div');
    this.previewBox.className =
      'w-12 h-12 rounded border-2 border-gray-300 dark:border-gray-600 shadow-sm transition-colors';
    this.previewBox.style.backgroundColor = this.currentColor;
    previewRow.appendChild(this.previewBox);

    // Hex input
    const hexInputWrapper = document.createElement('div');
    hexInputWrapper.className = 'flex-1';

    this.hexInput = document.createElement('input');
    this.hexInput.type = 'text';
    this.hexInput.value = this.currentColor.toUpperCase();
    this.hexInput.placeholder = '#000000';
    this.hexInput.maxLength = 7;
    this.hexInput.className =
      'w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400 dark:placeholder-gray-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100';
    hexInputWrapper.appendChild(this.hexInput);
    previewRow.appendChild(hexInputWrapper);

    wrapper.appendChild(previewRow);

    // Native color picker (hidden but functional)
    this.colorPicker.className = 'hidden';
    wrapper.appendChild(this.colorPicker);

    // Preset colors grid
    const presetsLabel = document.createElement('div');
    presetsLabel.className = 'text-xs font-medium text-gray-600 dark:text-gray-400 mt-3';
    presetsLabel.textContent = 'Preset Colors';
    wrapper.appendChild(presetsLabel);

    this.presetsContainer = document.createElement('div');
    this.presetsContainer.className = 'flex flex-wrap gap-2';
    this.presetsContainer.setAttribute('role', 'group');
    this.presetsContainer.setAttribute('aria-label', 'Preset color palette');

    PRESET_COLORS.forEach((color) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className =
        'preset-color w-8 h-8 rounded-full border-2 border-gray-300 dark:border-gray-600 hover:scale-110 transition-transform focus:outline-none focus:ring-2 focus:ring-blue-500';
      button.style.backgroundColor = color;
      button.dataset.color = color;
      button.title = color;
      button.setAttribute('aria-label', `Color ${color}`);

      if (this.presetsContainer) {
        this.presetsContainer.appendChild(button);
      }
    });

    wrapper.appendChild(this.presetsContainer);

    // Replace original input with wrapper
    this.container.appendChild(wrapper);

    // Keep original color text input hidden
    this.colorInput.className = 'hidden';
    this.container.appendChild(this.colorInput);
  }

  private setupEventListeners(): void {
    // Hex input change
    if (this.hexInput) {
      this.hexInput.addEventListener('input', (e) => {
        const value = (e.target as HTMLInputElement).value.trim();
        if (this.isValidHex(value)) {
          this.setColor(value);
        }
      });

      this.hexInput.addEventListener('blur', () => {
        // Reset to current color if invalid
        if (this.hexInput && !this.isValidHex(this.hexInput.value)) {
          this.hexInput.value = this.currentColor.toUpperCase();
        }
      });
    }

    // Native color picker change
    this.colorPicker.addEventListener('input', (e) => {
      const value = (e.target as HTMLInputElement).value;
      this.setColor(value);
    });

    // Preset color buttons
    if (this.presetsContainer) {
      this.presetsContainer.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        if (target.classList.contains('preset-color')) {
          const color = target.dataset.color;
          if (color) {
            this.setColor(color);
          }
        }
      });

      // Keyboard navigation
      this.presetsContainer.addEventListener('keydown', (e) => {
        const target = e.target as HTMLElement;
        if (!target.classList.contains('preset-color') || !this.presetsContainer) {
          return;
        }

        const buttons = Array.from(
          this.presetsContainer.querySelectorAll('.preset-color')
        ) as HTMLButtonElement[];
        const currentIndex = buttons.indexOf(target as HTMLButtonElement);

        let nextIndex = currentIndex;

        switch (e.key) {
          case 'ArrowRight':
            e.preventDefault();
            nextIndex = (currentIndex + 1) % buttons.length;
            break;
          case 'ArrowLeft':
            e.preventDefault();
            nextIndex = (currentIndex - 1 + buttons.length) % buttons.length;
            break;
          case 'ArrowDown':
            e.preventDefault();
            nextIndex = Math.min(currentIndex + 5, buttons.length - 1);
            break;
          case 'ArrowUp':
            e.preventDefault();
            nextIndex = Math.max(currentIndex - 5, 0);
            break;
          case 'Enter':
          case ' ': {
            e.preventDefault();
            const color = target.dataset.color;
            if (color) {
              this.setColor(color);
            }
            return;
          }
          case 'Escape':
            e.preventDefault();
            target.blur();
            return;
        }

        if (nextIndex !== currentIndex) {
          buttons[nextIndex]?.focus();
        }
      });
    }
  }

  private isValidHex(value: string): boolean {
    return /^#[0-9A-Fa-f]{6}$/.test(value);
  }

  private setColor(color: string): void {
    // Normalize to uppercase
    const normalizedColor = color.toUpperCase();

    if (!this.isValidHex(normalizedColor)) {
      return;
    }

    this.currentColor = normalizedColor;

    // Update all UI elements
    if (this.previewBox) {
      this.previewBox.style.backgroundColor = normalizedColor;
    }

    if (this.hexInput) {
      this.hexInput.value = normalizedColor;
    }

    this.colorPicker.value = normalizedColor.toLowerCase();
    this.colorInput.value = normalizedColor;

    // Update selected preset button
    this.updateSelectedPreset(normalizedColor);

    // Trigger onChange callback
    if (this.config.onChange) {
      this.config.onChange(normalizedColor);
    }
  }

  private updateSelectedPreset(color: string): void {
    // Remove previous selection
    if (this.selectedPresetButton) {
      this.selectedPresetButton.classList.remove('border-blue-500', 'border-4', 'scale-110');
      this.selectedPresetButton.classList.add(
        'border-gray-300',
        'dark:border-gray-600',
        'border-2'
      );
    }

    // Find and highlight matching preset
    if (this.presetsContainer) {
      const matchingButton = this.presetsContainer.querySelector(
        `button[data-color="${color}"]`
      ) as HTMLButtonElement;

      if (matchingButton) {
        matchingButton.classList.remove('border-gray-300', 'dark:border-gray-600', 'border-2');
        matchingButton.classList.add('border-blue-500', 'border-4', 'scale-110');
        this.selectedPresetButton = matchingButton;
      } else {
        this.selectedPresetButton = null;
      }
    }
  }

  public getColor(): string {
    return this.currentColor;
  }

  public destroy(): void {
    // Clean up event listeners if needed
    this.container.innerHTML = '';
  }
}

export function initializeColorPicker(config: ColorPickerConfig): ColorPicker {
  return new ColorPicker(config);
}
