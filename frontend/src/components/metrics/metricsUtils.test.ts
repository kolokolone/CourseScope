import { describe, expect, it } from 'vitest';

import { getValueAtPath, parsePath } from './metricsUtils';

describe('metricsUtils', () => {
  it('returns values safely with getValueAtPath', () => {
    const obj = { a: { b: { c: 1 } }, list: [{ x: 2 }] };
    expect(getValueAtPath(obj, 'a.b.c')).toBe(1);
    expect(getValueAtPath(obj, 'list.0.x')).toBe(2);
    expect(getValueAtPath(obj, 'missing.path')).toBeUndefined();
  });

  it('returns null for missing paths with parsePath', () => {
    const obj = { a: { b: 3 } };
    expect(parsePath(obj, 'a.b')).toBe(3);
    expect(parsePath(obj, 'a.c')).toBeNull();
  });
});
