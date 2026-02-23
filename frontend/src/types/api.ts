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
  activity_name?: string;
  started_at_utc?: string;
  summary: Record<string, unknown>;
  highlights: Record<string, unknown>;
  zones?: Record<string, unknown>;
  best_efforts?: Record<string, unknown>;
  personal_records?: Record<string, unknown>;
  segment_analysis?: Record<string, unknown>;
  performance_predictions?: Record<string, unknown>;
  pauses?: Record<string, unknown>;
  climbs?: Record<string, unknown>;
  splits?: Record<string, unknown>;
  garmin_summary?: Record<string, unknown>;
  cadence?: Record<string, unknown>;
  power?: Record<string, unknown>;
  running_dynamics?: Record<string, unknown>;
  power_advanced?: Record<string, unknown>;
  pacing?: Record<string, unknown>;
  training_load?: Record<string, unknown>;
  series_index: SeriesIndex;
  limits?: ActivityLimitsDetail;
}

export interface TheoreticalPaceElevationPoint {
  distance_km: number;
  target_pace_s_per_km: number;
  elevation_m?: number | null;
}

export interface GradeTimeBin {
  grade_bin_center_pct: number;
  label: string;
  time_s: number;
}

export interface PaceTimeBin {
  pace_bin_floor_s_per_km: number;
  label: string;
  time_s: number;
}

export interface TheoreticalTraceStatus {
  saved: boolean;
  trace_id?: string;
  trace_name?: string;
}

export interface TheoreticalActivityResponse extends RealActivityResponse {
  target_mode?: 'pace' | 'time';
  target_pace_s_per_km?: number;
  target_time_s?: number;
  vma_kmh?: number;
  pace_elevation_series?: TheoreticalPaceElevationPoint[];
  grade_time_bins?: GradeTimeBin[];
  pace_time_bins?: PaceTimeBin[];
  secondary_metrics?: Record<string, unknown>;
  trace_status?: TheoreticalTraceStatus;
}

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
  y: Array<number | null>;
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
  started_at?: string | null;
  stats_sidebar: SidebarStats;
  file_hash: string;
}

export interface ActivityLoadRequest {
  file: File;
  name?: string;
  activity_type?: 'real' | 'theoretical';
}

export interface GarminConnectResponse {
  status: string;
  mfa_session_id?: string | null;
}

export interface GarminSyncResponse {
  run_id: string;
  status: string;
  imported_count: number;
  skipped_count: number;
  cursor_time_utc?: string | null;
  error?: string | null;
}

export interface GarminCredentialsStatusResponse {
  configured: boolean;
  email?: string | null;
  path: string;
}

export interface GarminStatusResponse {
  tokens_present: boolean;
  tokens_dir: string;
  cursor_time_utc?: string | null;
  cursor_updated_at_utc?: string | null;
  last_run?: {
    id: string;
    source: string;
    started_at_utc: string;
    finished_at_utc?: string | null;
    status: string;
    imported_count: number;
    skipped_count: number;
    processed_count?: number;
    duration_s?: number | null;
    error?: string | null;
  } | null;
}

export interface SeriesRequest {
  activity_id: string;
  series_name: string;
  x_axis?: 'time' | 'distance';
  from?: number;
  to?: number;
  downsample?: number;
}

export interface PaceVsGradeBin {
  grade_center: number;
  pace_med_s_per_km: number;
  pace_std_s_per_km: number;
  pace_n: number;
  pro_pace_s_per_km?: number | null;
}

export interface ProPaceVsGradePoint {
  grade_percent: number;
  pace_s_per_km_pro: number;
}

export interface PaceVsGradeResponse {
  bins: PaceVsGradeBin[];
  pro_ref: ProPaceVsGradePoint[];
}

export interface TraceItem {
  id: string;
  name?: string | null;
  created_at_utc: string;
  distance_km: number;
  elevation_gain_m: number;
  elevation_loss_m?: number | null;
  elevation_min_m?: number | null;
  elevation_max_m?: number | null;
  original_filename?: string | null;
}

export interface TracesListResponse {
  traces: TraceItem[];
  sync?: {
    scanned: number;
    indexed: number;
    up_to_date: number;
    deleted: number;
    errors: number;
  };
}

export interface TraceUploadResponse {
  trace: TraceItem;
  activity_id: string;
}

export interface TraceOpenResponse {
  activity_id: string;
  trace_id: string;
}

export interface PersonalSettingsResponse {
  vma_kmh?: number | null;
  vo2max_lastest?: number | null;
  hr_max_manual_bpm?: number | null;
  hr_max_source: 'detected' | 'manual';
  hr_max_detected_bpm?: number | null;
  hr_max_effective_bpm?: number | null;
  updated_at_utc: string;
}

export type GoalRaceType = 'road' | 'trail';

export interface GoalItem {
  id: string;
  name: string;
  event_date: string;
  distance_km: number;
  location?: string | null;
  location_city?: string | null;
  location_country?: string | null;
  location_country_code?: string | null;
  location_lat?: number | null;
  location_lon?: number | null;
  target_time_s?: number | null;
  target_pace_s_per_km?: number | null;
  race_type: GoalRaceType;
  notes?: string | null;
  created_at_utc: string;
  updated_at_utc: string;
}

export interface GoalsListResponse {
  goals: GoalItem[];
}

export interface GeoCityItem {
  label: string;
  city: string;
  country: string;
  country_code?: string | null;
  lat: number;
  lon: number;
}

export interface GeoCitiesResponse {
  query: string;
  results: GeoCityItem[];
}

export interface RealActivityPaceElevationPoint {
  distance_km: number;
  pace_s_per_km: number;
  elevation_m?: number | null;
}

export interface RealActivityBinsResponse {
  pace_elevation_series: RealActivityPaceElevationPoint[];
  pace_time_bins: PaceTimeBin[];
  grade_time_bins: GradeTimeBin[];
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

// Progression (/progress/*)
export type ProgressType = 'real' | 'theoretical';
export type ProgressGroupBy = 'day' | 'week' | 'month';
export type ProgressAgg = 'sum' | 'avg';
export type ProgressSeriesMetric =
  | 'distance_m'
  | 'moving_time_s'
  | 'elapsed_time_s'
  | 'elevation_gain_m'
  | 'trimp'
  | 'aerobic_efficiency_m_s_per_bpm'
  | 'vo2max'
  | 'decoupling_pct'
  | (string & {});

export interface ProgressSeriesPoint {
  bucket_start: string;
  value: number;
}

export type ProgressSeriesResponse = ProgressSeriesPoint[];

export type ProgressBestEffortKind = 'pace_s_per_km' | (string & {});

export interface ProgressBestEffortPoint {
  activity_id: string;
  start_ts_utc: string;
  value: number;
  is_pr: boolean;
}

export interface ProgressBestEffortsResponse {
  points: ProgressBestEffortPoint[];
}

export interface ProgressActivity {
  activity_id: string;
  activity_type: ProgressType | string;
  start_ts_utc: string;
  distance_m: number | null;
  moving_time_s: number | null;
  elapsed_time_s: number | null;
  elevation_gain_m: number | null;
  avg_pace_s_per_km: number | null;
  best_pace_s_per_km: number | null;
  pace_threshold_s_per_km: number | null;
  avg_hr_bpm: number | null;
  max_hr_bpm: number | null;
  trimp: number | null;
  vo2max?: number | null;
  training_load_method: string | null;
  aerobic_efficiency_m_s_per_bpm: number | null;
  decoupling_pct: number | null;
  stability_cv: number | null;
  stability_iqr_ratio: number | null;
  has_hr: boolean;
  has_power: boolean;
  has_cadence: boolean;
  data_points: number | null;
  session_tag?: ProgressSessionTag | null;
  terrain_tag?: ProgressTerrainTag | null;
  race_marker?: boolean;
  tag_source?: 'auto' | 'manual' | string | null;
}

export interface ProgressActivitiesResponse {
  activities: ProgressActivity[];
}

export interface ProgressVerifyResult {
  scanned: number;
  indexed: number;
  up_to_date: number;
  errors: number;
}

export interface ProgressVerifyResponse {
  running: boolean;
  last_started_at_utc: string | null;
  last_finished_at_utc: string | null;
  last_error: string | null;
  last_result: ProgressVerifyResult | null;
}

export type ProgressIndexationMode = 'fast' | 'slow' | null;
export type ProgressIndexationPhase = 'prepare' | 'scan_fs' | 'sync_db' | 'recompute' | 'finalize' | null;
export type ProgressIndexationStrategy = 'incremental' | 'backfill_missing' | 'backfill_full';

export interface ProgressIndexationResult {
  scanned: number;
  added: number;
  deleted: number;
  indexed: number;
  up_to_date: number;
  errors: number;
  skipped: number;
}

export interface ProgressIndexStatusResponse {
  running: boolean;
  mode: ProgressIndexationMode;
  phase: ProgressIndexationPhase;
  current_run_duration_ms: number | null;
  progress_current: number;
  progress_total: number;
  percent: number;
  last_result: ProgressIndexationResult | null;
  last_error: string | null;
  last_started_at_utc: string | null;
  last_finished_at_utc: string | null;
  last_duration_ms: number | null;
}

export interface ProgressReferencePoint {
  activity_id: string;
  start_ts_utc: string;
  value: number;
}

export interface ProgressHrAtPaceSeries {
  pace_s_per_km: number;
  points: ProgressReferencePoint[];
}

export interface ProgressHrAtPaceResponse {
  series: ProgressHrAtPaceSeries[];
}

export interface ProgressPaceAtHrSeries {
  hr_bpm: number;
  points: ProgressReferencePoint[];
}

export interface ProgressPaceAtHrResponse {
  series: ProgressPaceAtHrSeries[];
}

export type ProgressSessionTag = 'easy' | 'tempo' | 'interval' | 'long_run' | 'unknown';
export type ProgressTerrainTag = 'flat' | 'rolling' | 'hilly' | 'unknown';

export interface ProgressTaxonomyCount {
  tag: string;
  count: number;
}

export interface ProgressSessionTaxonomyResponse {
  session_counts: ProgressTaxonomyCount[];
  terrain_counts: ProgressTaxonomyCount[];
  race_markers: number;
  total_tagged: number;
}

export interface ProgressPaceHrWaterfallPoint {
  pace_bin_s_per_km: number;
  hr_bpm: number;
  time_s_bin: number;
}

export interface ProgressPaceHrWaterfallActivity {
  activity_id: string;
  start_ts_utc: string;
  session_tag: ProgressSessionTag | string;
  terrain_tag: ProgressTerrainTag | string;
  race_marker: boolean;
  points: ProgressPaceHrWaterfallPoint[];
}

export interface ProgressPaceHrWaterfallResponse {
  activities: ProgressPaceHrWaterfallActivity[];
}
