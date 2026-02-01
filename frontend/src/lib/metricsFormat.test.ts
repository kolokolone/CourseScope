import { describe, expect, it } from 'vitest';

import {
  formatDurationSeconds,
  formatMeters,
  formatMetricValue,
  formatNumber,
  formatPaceSecondsPerKm,
  formatPercent,
  formatSpeedKmh,
} from './metricsFormat';

describe('metricsFormat', () => {
  it('formats duration seconds as hh:mm:ss or mm:ss', () => {
    expect(formatDurationSeconds(0)).toBe('00:00');
    expect(formatDurationSeconds(65)).toBe('01:05');
    expect(formatDurationSeconds(3661)).toBe('1:01:01');
  });

  it('formats pace seconds per km as mm:ss and preserves sign for deltas', () => {
    expect(formatPaceSecondsPerKm(270)).toBe('04:30');
    expect(formatPaceSecondsPerKm(-12, { forceSign: true })).toBe('-00:12');
    expect(formatPaceSecondsPerKm(12, { forceSign: true })).toBe('+00:12');
  });

  it('formats numbers and units consistently', () => {
    expect(formatNumber(3)).toBe('3');
    expect(formatNumber(3.14159)).toBe('3.14');
    expect(formatSpeedKmh(12.345)).toBe('12.3');
    expect(formatMeters(125.7)).toBe('126');
    expect(formatPercent(12.345)).toBe('12.3');
  });

  it('formats using metric format mapping', () => {
    expect(formatMetricValue(120, 'duration')).toBe('02:00');
    expect(formatMetricValue(285, 'pace')).toBe('04:45');
    expect(formatMetricValue(18.2, 'speed')).toBe('18.2');
    expect(formatMetricValue(42.5, 'meters')).toBe('43');
    expect(formatMetricValue(9.99, 'percent')).toBe('10.0');
  });

  it('handles text and boolean formats explicitly', () => {
    expect(formatMetricValue(undefined, 'text')).toBe('');
    expect(formatMetricValue(null, 'text')).toBe('');
    expect(formatMetricValue('hello', 'text')).toBe('hello');
    expect(formatMetricValue(123, 'text')).toBe('123');

    expect(formatMetricValue(undefined, 'boolean')).toBe('');
    expect(formatMetricValue(null, 'boolean')).toBe('');
    expect(formatMetricValue(true, 'boolean')).toBe('Yes');
    expect(formatMetricValue(false, 'boolean')).toBe('No');
    expect(formatMetricValue(1, 'boolean')).toBe('Yes');
    expect(formatMetricValue(0, 'boolean')).toBe('No');
  });
});
