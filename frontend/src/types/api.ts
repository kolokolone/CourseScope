declare const activityIdBrand: unique symbol;
declare const traceIdBrand: unique symbol;
declare const racePlanIdBrand: unique symbol;
declare const raceScenarioIdBrand: unique symbol;

export type ActivityId = string & { readonly [activityIdBrand]: 'ActivityId' };
export type TraceId = string & { readonly [traceIdBrand]: 'TraceId' };
export type RacePlanId = string & { readonly [racePlanIdBrand]: 'RacePlanId' };
export type RaceScenarioId = string & { readonly [raceScenarioIdBrand]: 'RaceScenarioId' };

export const asActivityId = (value: string) => value as ActivityId;
export const asTraceId = (value: string) => value as TraceId;

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
  id: ActivityId;
  type: 'real';
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

export interface RaceProfilePoint {
  distance_km: number;
  pace_s_per_km: number;
  elevation_m: number;
  grade_pct: number;
  grade_robust_pct: number;
  elapsed_time_s: number;
  passage_time_iso?: string | null;
  lat?: number | null;
  lon?: number | null;
}

export interface GradeTimeBin {
  grade_bin_center_pct: number;
  label: string;
  time_s: number;
  distance_km?: number;
  time_percent?: number;
  is_overflow?: boolean;
}

export interface PaceTimeBin {
  pace_bin_floor_s_per_km: number;
  label: string;
  time_s: number;
  pace_bin_ceiling_s_per_km?: number;
}

export interface SeriesMeta {
  downsampled?: boolean;
  original_points?: number;
  returned_points?: number;
}

export interface SeriesResponse {
  name: string;
  x_axis: 'time' | 'distance';
  x_unit: 's' | 'km';
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
  points?: Array<{ distance_km: number; lat: number; lon: number }>;
}

export interface ActivityMetadata {
  id: ActivityId;
  filename: string;
  name?: string;
  activity_type: 'real';
  created_at: string;
  started_at?: string | null;
  stats_sidebar: SidebarStats;
  file_hash: string;
}

export interface ActivityLoadRequest {
  file: File;
  name?: string;
  activity_type?: 'real';
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
  pace_std_w_s_per_km?: number | null;
  pace_n: number;
  pro_pace_s_per_km?: number | null;
  time_s_bin?: number | null;
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
  id: TraceId;
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
}

export type RaceObjectiveType = 'pace' | 'time' | 'effort';
export type RaceStopType = 'water' | 'nutrition' | 'assistance' | 'other';

export interface RaceStop {
  id: string;
  distance_km: number;
  stop_type: RaceStopType;
  duration_s: number;
  notes?: string | null;
  sort_order: number;
}

export interface RaceScenario {
  id: RaceScenarioId;
  race_plan_id: RacePlanId;
  name: string;
  objective_type: RaceObjectiveType;
  target_value: number;
  slope_model: 'minetti';
  vma_kmh?: number | null;
  calibration_factor: number;
  is_active: boolean;
  stops?: RaceStop[];
  strategy_segments?: RaceStrategySegment[];
  nutrition?: RaceNutritionItem[];
}

export interface RaceStrategySegment {
  id?: string;
  name?: string;
  start_distance_km: number;
  end_distance_km: number;
  target_pace_s_per_km?: number | null;
  notes?: string | null;
}

export interface RaceNutritionItem {
  id?: string;
  distance_km: number;
  item_type: 'nutrition' | 'hydration';
  amount?: string | null;
  notes?: string | null;
}

export interface RaceEquipmentItem {
  id?: string;
  label: string;
  is_checked: boolean;
  notes?: string | null;
  sort_order?: number;
}

export interface RaceCoursePoint {
  id?: string;
  distance_km: number;
  point_type: 'landmark' | 'custom_segment';
  label: string;
  end_distance_km?: number | null;
  notes?: string | null;
}

export interface RacePlan {
  id: RacePlanId;
  trace_id: TraceId;
  name: string;
  goal_id?: string | null;
  race_date?: string | null;
  start_time?: string | null;
  timezone: string;
  active_scenario_id?: RaceScenarioId | null;
  notes?: string | null;
  scenarios: RaceScenario[];
  equipment?: RaceEquipmentItem[];
  course_points?: RaceCoursePoint[];
}

export interface TraceDetailResponse {
  trace: TraceItem;
  file: {
    original_filename?: string | null;
    source_sha256: string;
    parquet_available: boolean;
    parquet_source: 'parquet' | 'rebuilt';
    parquet_rebuild_reason?: string | null;
    dataframe_schema_version: string;
    parquet_generated_at_utc: string;
  };
  static_metrics: { distance_km: number; elevation_gain_m: number; elevation_loss_m: number; elevation_min_m: number; elevation_max_m: number };
  quality: RaceDataQuality;
  active_plan?: RacePlan | null;
  plans: RacePlan[];
}

export interface RaceDataQuality {
  profile_version: string;
  distance_source: string;
  distance_unit: 'km';
  internal_distance_unit: 'm';
  grid_step_m: number;
  elevation_smoothing_window_m: number;
  robust_grade_window_m: number;
  robust_grade_method?: 'theil_sen_fixed_distance' | string;
  interpolated_elevation_ratio: number;
  corrected_or_rejected_source_ratio: number;
  corrected_elevation_ratio: number;
  sampling_density_points_per_km: number;
  signal_gap_count: number;
  maximum_signal_gap_m: number;
  altimetry_quality: 'high' | 'medium' | 'low';
  warnings: Array<{ code: string; message: string }>;
}

export interface RacePassage {
  distance_km: number;
  running_time_s: number;
  stop_time_s: number;
  elapsed_time_s: number;
  passage_time_iso?: string | null;
  elevation_m: number;
}

export interface RaceSplit {
  index: number;
  start_distance_km: number;
  end_distance_km: number;
  distance_km: number;
  running_time_s: number;
  stop_time_s: number;
  elapsed_time_s: number;
  pace_s_per_km: number;
}

export interface RaceClimb {
  id: string;
  start_distance_km: number;
  end_distance_km: number;
  distance_km: number;
  elevation_gain_m: number;
  average_grade_pct: number;
  running_time_s: number;
  elapsed_time_s: number;
  arrival_time_iso?: string | null;
}

export interface RaceHistogram<T> {
  complete_classes: T[];
  display_classes: T[];
  total_time_s: number;
  displayed_time_s: number;
  hidden_time_s: number;
}

export interface RacePlanPreview {
  pipeline_version: string;
  scenario_hash: string;
  units: { distance: 'km'; internal_distance: 'm'; elevation: 'm'; pace: 's/km'; time: 's'; grade: '%' };
  model: {
    slope_model: 'minetti';
    minetti_grade_limit_pct: number;
    minetti_uphill_compression_exponent: number;
    downhill_model: 'empirical_piecewise_linear';
    pace_smoothing_window_m: number;
  };
  totals: {
    distance_km: number;
    elevation_gain_m: number;
    elevation_loss_m: number;
    base_pace_s_per_km: number;
    average_pace_s_per_km: number;
    running_time_s: number;
    stop_time_s: number;
    elapsed_time_s: number;
    start_time_iso?: string | null;
    arrival_time_iso?: string | null;
    effort_distance_km: number;
  };
  profile: RaceProfilePoint[];
  passages: RacePassage[];
  splits: RaceSplit[];
  climbs: RaceClimb[];
  segments: Array<RaceStrategySegment & { id: string; name: string; distance_km: number; running_time_s: number; stop_time_s: number; elapsed_time_s: number; pace_s_per_km: number; elevation_gain_m: number }>;
  stops: RaceStop[];
  histograms: {
    pace: RaceHistogram<PaceTimeBin>;
    grade: RaceHistogram<GradeTimeBin>;
  };
  alerts: Array<{ code: string; message: string }>;
  calculated_strategy: RaceStrategySegment[];
  weather: { status: 'available' | 'assumptions' | 'unavailable'; source?: 'provider' | 'scenario' | null; data?: Record<string, unknown> | null; adjustment_factor?: number };
  quality: RaceDataQuality;
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
  pace_histogram: RaceHistogram<PaceTimeBin>;
  grade_histogram: RaceHistogram<GradeTimeBin>;
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

// Calendar heatmap
export interface CalendarDay {
  date: string;
  has_activity: boolean;
  distance_km: number | null;
  moving_time_s: number | null;
  activity_count: number;
}

export interface CalendarResponse {
  days: CalendarDay[];
  year: number;
  total_active_days: number;
  longest_streak: number;
  current_streak: number;
}

// Training load (ACWR / Monotony / Strain)
export interface TrainingLoadPoint {
  bucket_start: string;
  acute_load_7d: number | null;
  chronic_load_42d: number | null;
  acwr: number | null;
  monotony_7d: number | null;
  strain_7d: number | null;
}

export interface TrainingLoadResponse {
  points: TrainingLoadPoint[];
  current_acwr: number | null;
  current_monotony: number | null;
  current_strain: number | null;
  risk_zone: 'low' | 'moderate' | 'high' | null;
}

// Intensity Distribution
export interface IntensityDistributionPoint {
  bucket_start: string;
  z1_time_min: number;
  z2_time_min: number;
  z3_time_min: number;
  z4_time_min: number;
  z5_time_min: number;
  total_time_min: number;
}

export interface IntensityDistributionResponse {
  points: IntensityDistributionPoint[];
  zone_thresholds_bpm: { z1: number; z2: number; z3: number; z4: number; z5: number } | null;
}

// Long Run Dose
export interface LongRunDosePoint {
  bucket_start: string;
  distance_km: number;
  moving_time_h: number;
  activity_count: number;
  max_distance_km: number;
}

// VAM Trend
export interface VamTrendPoint {
  activity_id: string;
  start_ts_utc: string;
  vam_max_m_h: number;
}
