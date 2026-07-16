import { describe, expect, it } from 'vitest';

import { formatStopDurationInput, parseStopDurationInput } from './raceStops';

describe('race stop durations', () => {
  it('converts an mm:ss input without losing seconds', () => {
    expect(parseStopDurationInput('12:34')).toBe(754);
    expect(formatStopDurationInput(754)).toBe('12:34');
  });

  it('rejects malformed or overflowing seconds', () => {
    expect(parseStopDurationInput('2:60')).toBeNull();
    expect(parseStopDurationInput('-3')).toBeNull();
    expect(parseStopDurationInput('3.5')).toBeNull();
    expect(parseStopDurationInput('3:5')).toBeNull();
    expect(parseStopDurationInput('')).toBeNull();
  });

  it('treats whole numbers as minutes and trims outer spaces', () => {
    expect(parseStopDurationInput('3')).toBe(180);
    expect(parseStopDurationInput('0')).toBe(0);
    expect(parseStopDurationInput(' 120 ')).toBe(7_200);
  });
});
