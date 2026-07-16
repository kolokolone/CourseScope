import type { ProgressSeriesMetric } from '@/types/api';
import { REFERENCE_SERIES_COLORS } from '@/lib/chartColors';

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
export const SERIES_COLORS = REFERENCE_SERIES_COLORS;
