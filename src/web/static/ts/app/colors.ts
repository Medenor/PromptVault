/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { CategoryItem, TagInfo, TagItem } from './types';

let tagColorMap: Record<string, string> = {};
let categoryColorMap: Record<string, string> = {};
const colorTextCache = new Map<string, string>();

export function getTagColorMap(): Record<string, string> {
  return tagColorMap;
}

export function getCategoryColorMap(): Record<string, string> {
  return categoryColorMap;
}

export function resolveCssColor(color?: string | null): string | null {
  if (!color) {
    return null;
  }
  const trimmed = color.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith('#')) {
    return trimmed;
  }
  return `var(--color-${trimmed}, ${trimmed})`;
}

/**
 * Convert hex color to RGB
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1]!, 16),
        g: parseInt(result[2]!, 16),
        b: parseInt(result[3]!, 16),
      }
    : null;
}

/**
 * Convert RGB to HSL
 */
function rgbToHsl(r: number, g: number, b: number): { h: number; s: number; l: number } {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      case b:
        h = ((r - g) / d + 4) / 6;
        break;
    }
  }

  return { h, s, l };
}

/**
 * Convert HSL to RGB
 */
function hslToRgb(h: number, s: number, l: number): { r: number; g: number; b: number } {
  let r, g, b;

  if (s === 0) {
    r = g = b = l;
  } else {
    const hue2rgb = (p: number, q: number, t: number) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };

    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }

  return {
    r: Math.round(r * 255),
    g: Math.round(g * 255),
    b: Math.round(b * 255),
  };
}

/**
 * Convert RGB to hex
 */
function rgbToHex(r: number, g: number, b: number): string {
  return (
    '#' +
    [r, g, b]
      .map((x) => {
        const hex = x.toString(16);
        return hex.length === 1 ? '0' + hex : hex;
      })
      .join('')
  );
}

/**
 * Get soft/muted color scheme for tag pills (Option B design)
 * Converts any color (hex or named) to a light background + colored border + darker text
 */
export function getSoftMutedColorScheme(colorInput: string | undefined | null): {
  background: string;
  text: string;
  border: string;
} {
  // Resolve color to hex
  const borderColor = resolveCssColor(colorInput);
  if (!borderColor) {
    // Default fallback if no color provided
    return {
      background: '#f3f4f6',
      text: '#374151',
      border: '#d1d5db',
    };
  }

  // Convert to RGB
  const rgb = hexToRgb(borderColor);
  if (!rgb) {
    // Fallback if color parsing fails
    return {
      background: '#f3f4f6',
      text: '#374151',
      border: '#d1d5db',
    };
  }

  // Convert RGB to HSL
  const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);

  // Create soft/muted version:
  // - Reduce saturation to 60% (less aggressive, more recognizable)
  // - Increase lightness to 78% (light but more visible than 90%)
  const softHsl = {
    h: hsl.h,
    s: 0.6, // 60% saturation (more visible, less aggressive)
    l: 0.78, // 78% lightness (soft but not too pale)
  };

  // Create border color version:
  // - Keep hue
  // - Increase saturation to 70% (more vibrant)
  // - Set lightness to 52% (more visible)
  const borderHsl = {
    h: hsl.h,
    s: 0.7, // 70% saturation (more vibrant)
    l: 0.52, // 52% lightness (medium tone, more visible)
  };

  // Convert back to RGB and then to hex
  const softRgb = hslToRgb(softHsl.h, softHsl.s, softHsl.l);
  const borderRgb = hslToRgb(borderHsl.h, borderHsl.s, borderHsl.l);

  const background = rgbToHex(softRgb.r, softRgb.g, softRgb.b);
  const borderColorHex = rgbToHex(borderRgb.r, borderRgb.g, borderRgb.b);

  // Determine text color based on background luminance
  // Use darker text for light backgrounds
  const textColor = '#374151'; // dark gray (works well on light backgrounds)

  return {
    background,
    text: textColor,
    border: borderColorHex,
  };
}

export function getReadableTextColor(background: string): string {
  const cached = colorTextCache.get(background);
  if (cached) {
    return cached;
  }
  const swatch = document.createElement('span');
  swatch.style.backgroundColor = background;
  swatch.style.display = 'none';
  document.body.appendChild(swatch);
  const computed = window.getComputedStyle(swatch).backgroundColor;
  swatch.remove();

  const match = computed.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!match) {
    colorTextCache.set(background, '#374151');
    return '#374151';
  }
  const r = Number(match[1]) / 255;
  const g = Number(match[2]) / 255;
  const b = Number(match[3]) / 255;
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const textColor = luminance > 0.6 ? '#1f2937' : '#f9fafb';
  colorTextCache.set(background, textColor);
  return textColor;
}

export function buildPillStyleFilled(color?: string | null): string {
  const background = resolveCssColor(color);
  if (!background) {
    return '';
  }
  const textColor = getReadableTextColor(background);
  return ` style="background-color: ${background}; color: ${textColor};"`;
}

export function buildPillStyleOutline(color?: string | null): string {
  if (!color) {
    return '';
  }
  // Use soft/muted color scheme (Option B)
  const colorScheme = getSoftMutedColorScheme(color);
  return ` style="background-color: ${colorScheme.background}; color: ${colorScheme.text}; border-color: ${colorScheme.border};"`;
}

export function applyPromptColorStyles(): void {
  document.querySelectorAll<HTMLElement>('[data-category-pill]').forEach((pill) => {
    const category = pill.dataset.categoryName || '';
    const color = categoryColorMap[category];
    if (!color) {
      return;
    }
    const background = resolveCssColor(color);
    if (!background) {
      return;
    }
    pill.style.backgroundColor = background;
    pill.style.color = getReadableTextColor(background);
  });

  document.querySelectorAll<HTMLElement>('[data-tag-pill]').forEach((pill) => {
    const tagName = pill.dataset.tagName || '';
    const color = tagColorMap[tagName];
    if (!color) {
      return;
    }
    // Use soft/muted color scheme (Option B design)
    const colorScheme = getSoftMutedColorScheme(color);
    pill.style.backgroundColor = colorScheme.background;
    pill.style.color = colorScheme.text;
    pill.style.borderColor = colorScheme.border;
  });
}

export function normalizeTagItems(items: TagItem[]): TagInfo[] {
  return items.map((item) => ({
    name: item.name,
    count: item.count ?? item.usage_count ?? 0,
    color: item.color ?? null,
  }));
}

export function setTagColorMap(tags: TagInfo[]): void {
  tagColorMap = {};
  tags.forEach((tag) => {
    if (tag.color) {
      tagColorMap[tag.name] = tag.color;
    }
  });
}

export function setCategoryColorMap(items: CategoryItem[]): void {
  categoryColorMap = {};
  items.forEach((item) => {
    if (item.color) {
      categoryColorMap[item.name] = item.color;
    }
  });
}

export function clearCategoryColorMap(): void {
  categoryColorMap = {};
}
