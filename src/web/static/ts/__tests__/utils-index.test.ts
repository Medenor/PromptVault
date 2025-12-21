import { describe, expect, it } from 'vitest';
import * as utils from '@/utils';

describe('utils index', () => {
  it('exports core utilities', () => {
    expect(typeof utils.showElement).toBe('function');
    expect(typeof utils.apiFetch).toBe('function');
    expect(typeof utils.t).toBe('function');
    expect(typeof utils.showNotification).toBe('function');
  });
});
