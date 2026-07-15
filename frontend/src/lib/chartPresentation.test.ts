import { describe, expect, it } from 'vitest';

import { addVisualPace, PACE_VISUAL_SMOOTHING_DISTANCE_KM } from './chartPresentation';

describe('addVisualPace', () => {
  it('smooths the rendered line over 200 m without changing source pace or time fields', () => {
    const points = [
      { distance_km: 0, pace_s_per_km: 300, elapsed_time_s: 0 },
      { distance_km: 0.05, pace_s_per_km: 480, elapsed_time_s: 18 },
      { distance_km: 0.1, pace_s_per_km: 300, elapsed_time_s: 42 },
      { distance_km: 0.15, pace_s_per_km: 480, elapsed_time_s: 60 },
      { distance_km: 0.2, pace_s_per_km: 300, elapsed_time_s: 84 },
    ];

    const result = addVisualPace(points);

    expect(PACE_VISUAL_SMOOTHING_DISTANCE_KM).toBe(0.2);
    expect(points.map((point) => point.pace_s_per_km)).toEqual([300, 480, 300, 480, 300]);
    expect(result.map((point) => point.elapsed_time_s)).toEqual(points.map((point) => point.elapsed_time_s));
    expect(Math.max(...result.map((point) => point.visual_pace_s_per_km)) - Math.min(...result.map((point) => point.visual_pace_s_per_km)))
      .toBeLessThan(90);
  });
});
