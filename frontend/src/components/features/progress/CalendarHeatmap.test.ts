import { describe, expect, it } from 'vitest';

import type { CalendarDay } from '@/types/api';
import { getMonthLabels } from './CalendarHeatmap';

describe('calendar heatmap alignment', () => {
  it('places month labels on the same weekly columns as their days', () => {
    const padding = Array<CalendarDay | null>(3).fill(null);
    const days: CalendarDay[] = Array.from({ length: 32 }, (_, index) => ({
      date: new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10),
      has_activity: false,
      distance_km: null,
      moving_time_s: null,
      activity_count: 0,
    }));

    const labels = getMonthLabels([...padding, ...days]);

    expect(labels[0]).toEqual({ colIndex: 0, label: 'janv.' });
    expect(labels[1]).toEqual({ colIndex: 4, label: 'f\u00e9vr.' });
  });
});
