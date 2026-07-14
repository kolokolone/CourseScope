import { describe, expect, it } from 'vitest';

import { buildGradeTicks, buildSymmetricGradeDomain, buildVisibleGradeRows } from './GradeTimeBarChart';

describe('grade histogram display', () => {
  it('removes empty values and keeps a dynamic domain centered on zero', () => {
    const rows = buildVisibleGradeRows([
      { grade_bin_center_pct: -6, label: '-6.0 %', time_s: 120 },
      { grade_bin_center_pct: 0, label: '0.0 %', time_s: 0 },
      { grade_bin_center_pct: 3, label: '+3.0 %', time_s: 180 },
    ]);

    expect(rows.map((row) => row.grade_bin_center_pct)).toEqual([-6, 3]);
    expect(buildSymmetricGradeDomain(rows)).toEqual([-10, 10]);
    expect(buildGradeTicks([-10, 10])).toContain(0);
  });
});
