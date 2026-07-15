import { describe, expect, it } from 'vitest';

import { findMapPointAtDistance } from './ActivityBetaPage';
import { buildRobustPaceDomain } from './CompactAnalysisChart';
import { hideShortFinalSplit, splitPaceBarWidth, type SplitRow } from './SplitsCard';

function split(split_index: number, distance_km: number): SplitRow {
  return { split_index, distance_km, pace_s_per_km: 300, avg_hr_bpm: 140, elev_delta_m: 0, time_s: 300 };
}

describe('activity beta helpers', () => {
  it('hides only a final split shorter than 500 metres', () => {
    expect(hideShortFinalSplit([split(1, 1), split(2, 0.49)])).toHaveLength(1);
    expect(hideShortFinalSplit([split(1, 1), split(2, 0.5)])).toHaveLength(2);
  });

  it('selects a map coordinate by explicit distance', () => {
    const point = findMapPointAtDistance([
      { distance_km: 0, lat: 45, lon: 6 },
      { distance_km: 1, lat: 46, lon: 7 },
    ], 0.8);
    expect(point).toMatchObject({ lat: 46, lon: 7 });
  });

  it('uses a longer pace bar for a faster split', () => {
    expect(splitPaceBarWidth(280, 280, 360)).toBe(90);
    expect(splitPaceBarWidth(360, 280, 360)).toBe(10);
  });

  it('keeps isolated pace outliers from flattening the activity chart', () => {
    const domain = buildRobustPaceDomain([...Array.from({ length: 100 }, () => 300), 2_000]);
    expect(domain?.[1]).toBeLessThan(400);
  });
});
