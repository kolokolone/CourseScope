import { describe, expect, it } from 'vitest';

import { GRADE_BAR_SIZE_PX, buildGradeTicks, buildSymmetricGradeDomain, buildVisibleGradeRows, splitGradeRows } from './GradeTimeBarChart';

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

  it('keeps all dense long-course bins visible with an explicit bar width', () => {
    const denseBins = Array.from({ length: 81 }, (_, index) => ({
      grade_bin_center_pct: -20 + index * 0.5,
      label: `${-20 + index * 0.5} %`,
      time_s: 1 + index,
    }));
    expect(buildVisibleGradeRows(denseBins)).toHaveLength(81);
    expect(GRADE_BAR_SIZE_PX).toBeGreaterThan(0);
  });

  it('keeps overflow time auditable without including it in the regular domain', () => {
    const rows = [
      { grade_bin_center_pct: -20, label: '≤ −20 %', time_s: 2, is_overflow: true },
      { grade_bin_center_pct: -4, label: '-4.0 %', time_s: 120, is_overflow: false },
      { grade_bin_center_pct: 5, label: '+5.0 %', time_s: 180, is_overflow: false },
      { grade_bin_center_pct: 20, label: '≥ +20 %', time_s: 1, is_overflow: true },
    ];
    const split = splitGradeRows(rows);

    expect(split.regular.map((row) => row.grade_bin_center_pct)).toEqual([-4, 5]);
    expect(split.overflow.map((row) => row.time_s)).toEqual([2, 1]);
    expect(split.totalTimeS).toBe(303);
    expect(buildSymmetricGradeDomain(split.regular)).toEqual([-5, 5]);
  });
});
