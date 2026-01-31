// Reference curve (pro) used for "Allure vs Pente".
//
// Source of truth in this repo:
// - `backend/core/resources/pro_pace_vs_grade.csv`
// Columns: grade_percent, pace_s_per_km_pro
//
// This file is a UI-only mirror so the frontend can render the curve without
// touching backend endpoints or inventing values.

export type ProPaceVsGradePoint = {
  gradePercent: number;
  paceSPerKm: number;
};

export const PRO_PACE_VS_GRADE: ProPaceVsGradePoint[] = [
  { gradePercent: -10.0, paceSPerKm: 217.8 },
  { gradePercent: -9.0, paceSPerKm: 214.5 },
  { gradePercent: -8.0, paceSPerKm: 212.3 },
  { gradePercent: -7.0, paceSPerKm: 210.1 },
  { gradePercent: -6.0, paceSPerKm: 208.6 },
  { gradePercent: -5.0, paceSPerKm: 207.9 },
  { gradePercent: -4.0, paceSPerKm: 209.0 },
  { gradePercent: -3.0, paceSPerKm: 211.2 },
  { gradePercent: -2.0, paceSPerKm: 214.5 },
  { gradePercent: -1.0, paceSPerKm: 217.8 },
  { gradePercent: 0.0, paceSPerKm: 220.0 },
  { gradePercent: 1.0, paceSPerKm: 227.8 },
  { gradePercent: 2.0, paceSPerKm: 240.6 },
  { gradePercent: 3.0, paceSPerKm: 255.2 },
  { gradePercent: 4.0, paceSPerKm: 268.7 },
  { gradePercent: 5.0, paceSPerKm: 278.2 },
  { gradePercent: 6.0, paceSPerKm: 284.7 },
  { gradePercent: 7.0, paceSPerKm: 288.6 },
  { gradePercent: 8.0, paceSPerKm: 310.6 },
  { gradePercent: 9.0, paceSPerKm: 323.5 },
  { gradePercent: 10.0, paceSPerKm: 330.0 },
  { gradePercent: 11.0, paceSPerKm: 336.5 },
  { gradePercent: 12.0, paceSPerKm: 349.4 },
  { gradePercent: 13.0, paceSPerKm: 368.8 },
  { gradePercent: 14.0, paceSPerKm: 388.2 },
  { gradePercent: 15.0, paceSPerKm: 407.6 },
];
