import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import { SERIES_COLORS } from './constants';
import { CHART_COLORS } from '@/lib/chartColors';

describe('ProgressHrPaceCharts colors', () => {
  it('uses the same three documented non-gray reference colors in both charts', () => {
    expect(SERIES_COLORS).toEqual([
      CHART_COLORS.theoreticalPace,
      CHART_COLORS.pace,
      CHART_COLORS.power,
    ]);
    expect(new Set(SERIES_COLORS).size).toBe(3);

    const source = readFileSync(
      resolve(process.cwd(), 'src/components/features/progress/ProgressHrPaceCharts.tsx'),
      'utf8',
    );
    expect(source.match(/stroke=\{SERIES_COLORS\[idx % SERIES_COLORS\.length\]\}/g)).toHaveLength(2);
    expect(source.match(/stroke=\{CHART_COLORS\.running\}/g)).toHaveLength(2);
  });
});
