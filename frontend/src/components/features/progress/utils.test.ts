import { describe, expect, it } from 'vitest';

import { vo2maxDomain } from './utils';

describe('vo2maxDomain', () => {
  it('starts at exactly 80 percent of the lowest visible value', () => {
    expect(vo2maxDomain([50, 55, 60])).toEqual([40, 61]);
  });

  it('keeps a positive domain when all values are equal', () => {
    expect(vo2maxDomain([50, 50])).toEqual([40, 55]);
  });
});
