import { describe, expect, it } from 'vitest';

import {
  formatDurationTarget,
  formatPaceTarget,
  formatRaceTarget,
  parseDurationTarget,
  parsePaceTarget,
  parseRaceTarget,
} from './raceTargetFormat';

describe('race target formatting', () => {
  it('formats and parses pace targets as min/km', () => {
    expect(formatPaceTarget(330)).toBe('5:30');
    expect(parsePaceTarget('5:30')).toBe(330);
    expect(parsePaceTarget('5:75')).toBeNull();
  });

  it('formats and parses total targets as hh:mm:ss', () => {
    expect(formatDurationTarget(13_505)).toBe('03:45:05');
    expect(parseDurationTarget('03:45:05')).toBe(13_505);
    expect(parseDurationTarget('3:75:05')).toBeNull();
  });

  it('displays effort as a VMA percentage while keeping the API ratio', () => {
    expect(formatRaceTarget('effort', 0.75)).toBe('75');
    expect(parseRaceTarget('effort', '75')).toBe(0.75);
  });
});
