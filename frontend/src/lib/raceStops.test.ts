import { describe, expect, it } from 'vitest';

import { formatStopDurationInput, parseStopDurationInput } from './raceStops';

describe('race stop durations', () => {
  it('converts an mm:ss input without losing seconds', () => {
    expect(parseStopDurationInput('12:34')).toBe(754);
    expect(formatStopDurationInput(754)).toBe('12:34');
  });

  it('rejects malformed or overflowing seconds', () => {
    expect(parseStopDurationInput('2:60')).toBeNull();
    expect(parseStopDurationInput('120')).toBeNull();
  });
});
