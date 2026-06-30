import type { ProgressSeriesMetric, ProgressSessionTag, ProgressTerrainTag } from '@/types/api';

export type VolumeMetricSpec = {
  metric: ProgressSeriesMetric;
  label: string;
  unit: string;
  convert: (raw: number) => number;
  decimals: number;
};

export const VOLUME_METRICS: VolumeMetricSpec[] = [
  {
    metric: 'distance_m',
    label: 'Volume hebdo',
    unit: 'km',
    convert: (raw) => raw / 1000,
    decimals: 1,
  },
  {
    metric: 'moving_time_s',
    label: 'Temps en mouvement',
    unit: 'h',
    convert: (raw) => raw / 3600,
    decimals: 1,
  },
  {
    metric: 'elevation_gain_m',
    label: 'Denivele positif',
    unit: 'm',
    convert: (raw) => raw,
    decimals: 0,
  },
];

export const HR_AT_PACE_REFS = [300, 330, 360] as const;
export const PACE_AT_HR_REFS = [140, 150, 160] as const;
export const SERIES_COLORS = ['#0f172a', '#334155', '#64748b', '#93c5fd', '#16a34a'];

export const SESSION_FILTER_OPTIONS: Array<{ value: 'all' | ProgressSessionTag; label: string }> = [
  { value: 'all', label: 'Toutes' },
  { value: 'easy', label: 'Easy' },
  { value: 'tempo', label: 'Tempo' },
  { value: 'interval', label: 'Interval' },
  { value: 'long_run', label: 'Long run' },
  { value: 'unknown', label: 'Unknown' },
];

export const TERRAIN_FILTER_OPTIONS: Array<{ value: 'all' | ProgressTerrainTag; label: string }> = [
  { value: 'all', label: 'Tous terrains' },
  { value: 'flat', label: 'Flat' },
  { value: 'rolling', label: 'Rolling' },
  { value: 'hilly', label: 'Hilly/Trail' },
  { value: 'unknown', label: 'Unknown' },
];
