import { describe, expect, it } from 'vitest';

import { buildSymmetricGradeRows } from './GradeTimeBarChart';

describe('buildSymmetricGradeRows', () => {
  it('keeps zero exactly in the middle of the -20/+20 visual range', () => {
    const rows = buildSymmetricGradeRows([
      { grade_bin_center_pct: 5, label: '+5.0 %', time_s: 120 },
    ]);

    expect(rows).toHaveLength(81);
    expect(rows[0]?.grade_bin_center_pct).toBe(-20);
    expect(rows[40]?.grade_bin_center_pct).toBe(0);
    expect(rows[80]?.grade_bin_center_pct).toBe(20);
    expect(rows.find((row) => row.grade_bin_center_pct === 5)?.time_s).toBe(120);
  });
});
