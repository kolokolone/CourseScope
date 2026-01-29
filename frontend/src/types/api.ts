export interface SidebarStats {
  distance_km?: number;
  elapsed_time_s?: number;
  moving_time_s?: number;
  elevation_gain_m?: number;
}

export interface ActivityLimits {
  downsampled: boolean;
  dataframe_limit?: number;
  note?: string;
}

export interface ActivityLoadResponse {
  id: string;
  type: 'real' | 'theoretical';
  stats_sidebar: SidebarStats;
  limits?: ActivityLimits;
}

export interface SeriesInfo {
  name: string;
  unit: string;
  x_axes: Array<'time' | 'distance'>;
  default: boolean;
}

export interface SeriesIndex {
  available: SeriesInfo[];
}

export interface ActivityLimitsDetail {
  downsampled: boolean;
  original_points?: number;
  returned_points?: number;
  note?: string;
}

export interface RealActivityResponse {
  summary: Record<string, unknown>;
  highlights: Record<string, unknown>;
  zones?: Record<string, unknown>;
  best_efforts?: Record<string, unknown>;
  pauses?: Record<string, unknown>;
  climbs?: Record<string, unknown>;
  splits?: Record<string, unknown>;
  garmin_summary?: Record<string, unknown>;
  cadence?: Record<string, unknown>;
  power?: Record<string, unknown>;
  running_dynamics?: Record<string, unknown>;
  power_advanced?: Record<string, unknown>;
  pacing?: Record<string, unknown>;
  series_index: SeriesIndex;
  limits?: ActivityLimitsDetail;
}

export type TheoreticalActivityResponse = RealActivityResponse;

export interface SeriesMeta {
  downsampled?: boolean;
  original_points?: number;
  returned_points?: number;
}

export interface SeriesResponse {
  name: string;
  x_axis: 'time' | 'distance';
  unit: string;
  x: number[];
  y: number[];
  meta?: SeriesMeta;
}

export interface MapMarker {
  lat: number;
  lon: number;
  label?: string;
  type?: string;
}

export interface ActivityMapResponse {
  bbox?: number[];
  polyline?: number[][];
  markers?: MapMarker[];
}

export interface ActivityMetadata {
  id: string;
  filename: string;
  name?: string;
  activity_type: 'real' | 'theoretical';
  created_at: string;
  stats_sidebar: SidebarStats;
  file_hash: string;
}

export interface ActivityLoadRequest {
  file: File;
  name?: string;
}

export interface SeriesRequest {
  activity_id: string;
  series_name: string;
  x_axis?: 'time' | 'distance';
  from?: number;
  to?: number;
  downsample?: number;
}

export interface ChartPoint {
  x: number;
  y: number;
}

export interface ChartData {
  [seriesName: string]: ChartPoint[];
}

export type TimeUnit = 'seconds' | 'minutes' | 'hours';
export type DistanceUnit = 'meters' | 'kilometers' | 'miles';
export type PaceUnit = 's_per_km' | 'min_per_km' | 'min_per_mile';
