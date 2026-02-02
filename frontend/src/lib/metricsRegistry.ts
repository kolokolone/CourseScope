import type { MetricFormat } from '@/lib/metricsFormat';

export type MetricAvailability = 'both' | 'fit' | 'cond';

export type MetricItem = {
  id: string;
  path: string;
  label: string;
  format?: MetricFormat;
  unit?: string;
  availability?: MetricAvailability;
  metricKey?: string;
};

export type MetricTableColumn = {
  key: string;
  label: string;
  align?: 'left' | 'center' | 'right';
  format?: MetricFormat;
  unit?: string;
  integer?: boolean;
};

export type MetricSection = {
  id: string;
  title: string;
  description?: string;
  category: string;
  kind: 'grid' | 'table' | 'list' | 'dataframe';
  gridColumns?: 4 | 6;
  hidden?: boolean;
  items?: MetricItem[];
  rowsPath?: string;
  columns?: MetricTableColumn[];
  listPath?: string;
  dataframes?: Array<{ id: string; title: string; path: string; columns?: string[] }>;
};

export type ChartSeriesDefinition = {
  name: string;
  label: string;
  availability: MetricAvailability;
  unit?: string;
  format?: MetricFormat;
};

export const CATEGORY_COLORS: Record<string, string> = {
  Resume: '#0072B2',
  Cardio: '#D55E00',
  'Allure/Vitesse': '#009E73',
  Relief: '#E69F00',
  Pacing: '#56B4E9',
  Cadence: '#F0E442',
  Puissance: '#CC79A7',
  Zones: '#0072B2',
  Splits: '#009E73',
  Climbs: '#56B4E9',
  'Running dynamics': '#CC79A7',
  Highlights: '#D55E00',
  Limits: '#999999',
  'Series index': '#0072B2',
  Charts: '#009E73',
  Map: '#E69F00',
};

export const KPI_METRICS: MetricItem[] = [
  {
    id: 'distance',
    path: 'summary.distance_km',
    label: 'Distance',
    format: 'number',
    unit: 'km',
    availability: 'both',
  },
  {
    id: 'total_time',
    path: 'summary.total_time_s',
    label: 'Temps total',
    format: 'duration',
    availability: 'both',
  },
  {
    id: 'avg_pace',
    path: 'summary.average_pace_s_per_km',
    label: 'Allure moyenne',
    format: 'pace',
    unit: '/ km',
    availability: 'both',
  },
  {
    id: 'elevation_gain',
    path: 'summary.elevation_gain_m',
    label: 'D+',
    format: 'meters',
    unit: 'm',
    availability: 'both',
  },
  {
    id: 'hr_avg',
    path: 'summary.cardio.hr_avg_bpm',
    label: 'FC moyenne',
    format: 'integer',
    unit: 'bpm',
    availability: 'fit',
  },
  {
    id: 'hr_max',
    path: 'summary.cardio.hr_max_bpm',
    label: 'FC max',
    format: 'integer',
    unit: 'bpm',
    availability: 'fit',
  },
];

export const ACTIVITY_LOAD_METRICS: MetricItem[] = [
  { id: 'load_distance', path: 'stats_sidebar.distance_km', label: 'Distance', format: 'number', unit: 'km' },
  { id: 'load_elapsed', path: 'stats_sidebar.elapsed_time_s', label: 'Temps total', format: 'duration' },
  { id: 'load_moving', path: 'stats_sidebar.moving_time_s', label: 'Temps en mouvement', format: 'duration' },
  { id: 'load_elev_gain', path: 'stats_sidebar.elevation_gain_m', label: 'D+', format: 'meters', unit: 'm' },
  { id: 'load_downsampled', path: 'limits.downsampled', label: 'Downsampled', format: 'boolean' },
  { id: 'load_dataframe_limit', path: 'limits.dataframe_limit', label: 'Dataframe limit', format: 'integer' },
  { id: 'load_note', path: 'limits.note', label: 'Note', format: 'text' },
];

export const REAL_METRIC_SECTIONS: MetricSection[] = [
  {
    id: 'summary',
    title: 'Infos de course',
    description: 'Essentiel de la sortie.',
    category: 'Resume',
    kind: 'grid',
    items: [
      { id: 'distance_km', path: 'summary.distance_km', label: 'Distance', format: 'number', unit: 'km' },
      { id: 'total_time_s', path: 'summary.total_time_s', label: 'Temps total', format: 'duration' },
      { id: 'moving_time_s', path: 'summary.moving_time_s', label: 'Temps en mouvement', format: 'duration' },
      {
        id: 'average_pace_s_per_km',
        path: 'summary.average_pace_s_per_km',
        label: 'Allure moyenne',
        format: 'pace',
        unit: '/ km',
      },
      {
        id: 'average_speed_kmh',
        path: 'summary.average_speed_kmh',
        label: 'Vitesse moyenne',
        format: 'speed',
        unit: 'km/h',
      },
      { id: 'elevation_gain_m', path: 'summary.elevation_gain_m', label: 'D+', format: 'meters', unit: 'm' },
    ],
  },
  {
    id: 'cardio',
    title: 'Cardio',
    description: "Lecture simple de l'effort (si FC presente).",
    category: 'Cardio',
    kind: 'grid',
    gridColumns: 6,
    items: [
      { id: 'hr_avg_bpm', path: 'summary.cardio.hr_avg_bpm', label: 'FC moyenne', format: 'integer', unit: 'bpm' },
      { id: 'hr_min_bpm', path: 'summary.cardio.hr_min_bpm', label: 'FC min', format: 'integer', unit: 'bpm' },
      { id: 'hr_max_bpm', path: 'summary.cardio.hr_max_bpm', label: 'FC max', format: 'integer', unit: 'bpm' },
      { id: 'cardiac_drift_pct', path: 'pacing.cardiac_drift_pct', label: 'Derive cardio', format: 'percent', unit: '%' },
      {
        id: 'cardiac_drift_slope_pct',
        path: 'pacing.cardiac_drift_slope_pct',
        label: 'Pente derive cardio',
        format: 'percent',
        unit: '%',
      },
    ],
  },
  {
    id: 'garmin-summary',
    title: 'Summary',
    description: 'Resume Garmin et variabilite.',
    category: 'Resume',
    kind: 'grid',
    gridColumns: 6,
    items: [
      { id: 'garmin_distance', path: 'garmin_summary.distance_km', label: 'Distance', format: 'number', unit: 'km' },
      { id: 'garmin_total_time', path: 'garmin_summary.total_time_s', label: 'Temps total', format: 'duration' },
      { id: 'garmin_moving_time', path: 'garmin_summary.moving_time_s', label: 'Temps en mouvement', format: 'duration' },
      { id: 'garmin_pause_time', path: 'garmin_summary.pause_time_s', label: "Temps a l'arret", format: 'duration' },
      {
        id: 'garmin_moving_distance',
        path: 'garmin_summary.moving_distance_km',
        label: 'Distance en mouvement',
        format: 'number',
        unit: 'km',
      },
      {
        id: 'garmin_avg_pace',
        path: 'garmin_summary.average_pace_s_per_km',
        label: 'Allure moyenne',
        format: 'pace',
        unit: '/ km',
      },
      {
        id: 'garmin_avg_speed',
        path: 'garmin_summary.average_speed_kmh',
        label: 'Vitesse moyenne',
        format: 'speed',
        unit: 'km/h',
      },
      {
        id: 'garmin_best_pace',
        path: 'garmin_summary.best_pace_s_per_km',
        label: 'Meilleure allure',
        format: 'pace',
        unit: '/ km',
      },
      { id: 'garmin_max_speed', path: 'garmin_summary.max_speed_kmh', label: 'Vitesse max', format: 'speed', unit: 'km/h' },
      {
        id: 'garmin_gap_mean',
        path: 'garmin_summary.gap_mean_s_per_km',
        label: 'GAP moyen',
        format: 'pace',
        unit: '/ km',
      },
      { id: 'elev_gain', path: 'garmin_summary.elevation_gain_m', label: 'D+', format: 'meters', unit: 'm' },
      { id: 'elev_loss', path: 'garmin_summary.elevation_loss_m', label: 'D-', format: 'meters', unit: 'm' },
      {
        id: 'elev_gain_filtered',
        path: 'garmin_summary.elevation_gain_filtered_m',
        label: 'D+ filtre',
        format: 'meters',
        unit: 'm',
      },
      {
        id: 'elev_loss_filtered',
        path: 'garmin_summary.elevation_loss_filtered_m',
        label: 'D- filtre',
        format: 'meters',
        unit: 'm',
      },
      { id: 'elev_min', path: 'garmin_summary.elevation_min_m', label: 'Altitude min', format: 'meters', unit: 'm' },
      { id: 'elev_max', path: 'garmin_summary.elevation_max_m', label: 'Altitude max', format: 'meters', unit: 'm' },
      { id: 'grade_mean', path: 'garmin_summary.grade_mean_pct', label: 'Pente moyenne', format: 'percent', unit: '%' },
      { id: 'grade_min', path: 'garmin_summary.grade_min_pct', label: 'Pente min', format: 'percent', unit: '%' },
      { id: 'grade_max', path: 'garmin_summary.grade_max_pct', label: 'Pente max', format: 'percent', unit: '%' },
      { id: 'vam', path: 'garmin_summary.vam_m_h', label: 'VAM', format: 'number', unit: 'm/h' },
      { id: 'steps_total', path: 'garmin_summary.steps_total', label: 'Pas total', format: 'integer' },
      { id: 'step_length', path: 'garmin_summary.step_length_est_m', label: 'Longueur de pas', format: 'meters', unit: 'm' },
      { id: 'longest_pause', path: 'garmin_summary.longest_pause_s', label: 'Pause max', format: 'duration' },
      { id: 'pace_median', path: 'garmin_summary.pace_median_s_per_km', label: 'Allure mediane', format: 'pace', unit: '/ km' },
      { id: 'pace_p10', path: 'garmin_summary.pace_p10_s_per_km', label: 'Allure P10', format: 'pace', unit: '/ km' },
      { id: 'pace_p90', path: 'garmin_summary.pace_p90_s_per_km', label: 'Allure P90', format: 'pace', unit: '/ km' },
      { id: 'pace_median_raw', path: 'garmin_summary.pace_median', label: 'Pace median', format: 'number' },
      { id: 'pace_p10_raw', path: 'garmin_summary.pace_p10', label: 'Pace P10', format: 'number' },
      { id: 'pace_p90_raw', path: 'garmin_summary.pace_p90', label: 'Pace P90', format: 'number' },
    ],
  },
  {
    id: 'pacing',
    title: 'Pacing',
    description: 'Equilibre et regularite.',
    category: 'Pacing',
    kind: 'grid',
    gridColumns: 6,
    items: [
      { id: 'pace_first_half', path: 'pacing.pace_first_half_s_per_km', label: '1re moitie', format: 'pace', unit: '/ km' },
      { id: 'pace_second_half', path: 'pacing.pace_second_half_s_per_km', label: '2e moitie', format: 'pace', unit: '/ km' },
      { id: 'pace_delta', path: 'pacing.pace_delta_s_per_km', label: 'Ecart (2e - 1re)', unit: '/ km' },
      {
        id: 'drift_s_per_km_per_km',
        path: 'pacing.drift_s_per_km_per_km',
        label: 'Drift allure',
        format: 'number',
        unit: 's/km/km',
      },
      { id: 'stability_cv', path: 'pacing.stability_cv', label: 'Stabilite CV', format: 'number' },
      { id: 'stability_iqr', path: 'pacing.stability_iqr_ratio', label: 'Stabilite IQR', format: 'number' },
      { id: 'gap_residual', path: 'pacing.gap_residual_median_s', label: 'GAP residual', format: 'duration' },
      {
        id: 'pace_threshold',
        path: 'pacing.pace_threshold_s_per_km',
        label: 'Seuil allure',
        format: 'pace',
        unit: '/ km',
      },
    ],
  },
  {
    id: 'cadence',
    title: 'Cadence',
    description: 'Disponible si la cadence est presente.',
    category: 'Cadence',
    kind: 'grid',
    gridColumns: 6,
    items: [
      { id: 'mean_spm', path: 'cadence.mean_spm', label: 'Cadence moyenne', format: 'integer', unit: 'spm' },
      { id: 'max_spm', path: 'cadence.max_spm', label: 'Cadence max', format: 'integer', unit: 'spm' },
      { id: 'target_spm', path: 'cadence.target_spm', label: 'Cible', format: 'integer', unit: 'spm' },
      { id: 'above_target_pct', path: 'cadence.above_target_pct', label: 'Temps au-dessus cible', format: 'percent', unit: '%' },
    ],
  },
  {
    id: 'power',
    title: 'Puissance',
    description: 'Disponible si la puissance est presente.',
    category: 'Puissance',
    kind: 'grid',
    gridColumns: 6,
    items: [
      { id: 'mean_w', path: 'power.mean_w', label: 'Puissance moyenne', format: 'integer', unit: 'W' },
      { id: 'max_w', path: 'power.max_w', label: 'Puissance max', format: 'integer', unit: 'W' },
      { id: 'ftp_w', path: 'power.ftp_w', label: 'FTP', format: 'integer', unit: 'W' },
      { id: 'ftp_estimated', path: 'power.ftp_estimated', label: 'FTP estime', format: 'boolean' },
      { id: 'normalized_power', path: 'power_advanced.normalized_power_w', label: 'Normalized power', format: 'integer', unit: 'W' },
      { id: 'intensity_factor', path: 'power_advanced.intensity_factor', label: 'Intensity factor', format: 'number' },
      { id: 'tss', path: 'power_advanced.tss', label: 'TSS', format: 'number' },
    ],
  },
  {
    id: 'running-dynamics',
    title: 'Running dynamics',
    description: 'Disponible si le fichier contient les running dynamics.',
    category: 'Running dynamics',
    kind: 'grid',
    gridColumns: 6,
    items: [
      { id: 'stride_length', path: 'running_dynamics.stride_length_mean_m', label: 'Longueur de foulee', format: 'meters', unit: 'm' },
      {
        id: 'vertical_oscillation',
        path: 'running_dynamics.vertical_oscillation_mean_cm',
        label: 'Oscillation verticale',
        format: 'number',
        unit: 'cm',
      },
      {
        id: 'vertical_ratio',
        path: 'running_dynamics.vertical_ratio_mean_pct',
        label: 'Vertical ratio',
        format: 'percent',
        unit: '%',
      },
      {
        id: 'ground_contact',
        path: 'running_dynamics.ground_contact_time_mean_ms',
        label: 'Temps de contact',
        format: 'integer',
        unit: 'ms',
      },
      {
        id: 'gct_balance',
        path: 'running_dynamics.gct_balance_mean_pct',
        label: 'GCT balance',
        format: 'percent',
        unit: '%',
      },
    ],
  },
  {
    id: 'zones',
    title: 'Zones',
    description: 'Repartition du temps par zones (FC / allure / puissance).',
    category: 'Zones',
    kind: 'dataframe',
    dataframes: [
      { id: 'zones-hr', title: 'Zones FC', path: 'zones.heart_rate', columns: ['zone', 'range', 'time_s', 'time_pct'] },
      { id: 'zones-pace', title: 'Zones allure', path: 'zones.pace', columns: ['zone', 'range', 'time_s', 'time_pct'] },
      { id: 'zones-power', title: 'Zones puissance', path: 'zones.power', columns: ['zone', 'range', 'time_s', 'time_pct'] },
    ],
  },
  {
    id: 'power-zones',
    title: 'Zones puissance (power.zones)',
    description: 'Zones de puissance calculees.',
    category: 'Zones',
    kind: 'dataframe',
    hidden: true,
    dataframes: [
      {
        id: 'power-zones',
        title: 'Zones puissance',
        path: 'power.zones',
        columns: ['zone', 'range', 'time_s', 'time_pct'],
      },
    ],
  },
  {
    id: 'power-duration-curve',
    title: 'Power duration curve',
    description: 'Puissance moyenne maximale par duree.',
    category: 'Puissance',
    kind: 'table',
    rowsPath: 'power_advanced.power_duration_curve',
    columns: [
      { key: 'duration_s', label: 'Duree', format: 'duration' },
      { key: 'power_w', label: 'Puissance', format: 'integer', unit: 'W' },
    ],
  },
  {
    id: 'highlights',
    title: 'Highlights',
    description: 'Ce qu’il faut retenir en une minute.',
    category: 'Highlights',
    kind: 'list',
    listPath: 'highlights.items',
  },
  {
    id: 'best-efforts',
    title: 'Efforts',
    description: 'Meilleurs temps sur des distances classiques.',
    category: 'Highlights',
    kind: 'table',
    rowsPath: 'best_efforts.rows',
    columns: [
      { key: 'distance_km', label: 'Distance', format: 'number', unit: 'km' },
      { key: 'time_s', label: 'Temps', format: 'duration' },
      { key: 'pace_s_per_km', label: 'Allure', format: 'pace', unit: '/ km' },
    ],
  },
  {
    id: 'personal-records',
    title: 'Personal records',
    description: 'Records personnels.',
    category: 'Highlights',
    kind: 'table',
    rowsPath: 'personal_records.rows',
    columns: [
      { key: 'distance_km', label: 'Distance', format: 'number', unit: 'km' },
      { key: 'time_s', label: 'Temps', format: 'duration' },
      { key: 'pace_s_per_km', label: 'Allure', format: 'pace', unit: '/ km' },
    ],
  },
  {
    id: 'segment-analysis',
    title: 'Segment analysis (time best efforts)',
    description: 'Meilleurs temps par segment.',
    category: 'Highlights',
    kind: 'table',
    rowsPath: 'segment_analysis.rows',
    columns: [
      { key: 'duration_s', label: 'Duree', format: 'duration' },
      { key: 'distance_km', label: 'Distance', format: 'number', unit: 'km' },
      { key: 'time_s', label: 'Temps', format: 'duration' },
      { key: 'pace_s_per_km', label: 'Allure', format: 'pace', unit: '/ km' },
    ],
  },
  {
    id: 'splits',
    title: 'Splits',
    description: 'Decoupage par km (ou proche), utile pour la regularite.',
    category: 'Splits',
    kind: 'table',
    rowsPath: 'splits.rows',
    columns: [
      { key: 'split_index', label: 'Split', format: 'integer' },
      { key: 'distance_km', label: 'Distance', format: 'number', unit: 'km' },
      { key: 'time_s', label: 'Temps', format: 'duration' },
      { key: 'pace_s_per_km', label: 'Allure', format: 'pace', unit: '/ km' },
      { key: 'elevation_gain_m', label: 'D+', format: 'meters', unit: 'm' },
    ],
  },
  {
    id: 'pacing-horizontal-splits',
    title: 'Temps intermédiaires',
    description: 'Table avec barres horizontales des splits par km.',
    category: 'Pacing',
    kind: 'table',
    gridColumns: 6,
    rowsPath: 'splits.rows',
    columns: [
      { key: 'km', label: 'Km', align: 'left' },
      { key: 'pace', label: 'Allure', align: 'left' },
      { key: 'bar', label: '', align: 'center' },
      { key: 'elevation', label: 'Élév.', align: 'right' },
      { key: 'hr', label: 'FC', align: 'right' },
    ],
  },
  {
    id: 'pauses',
    title: 'Pauses',
    description: 'Evenements de pause detectes.',
    category: 'Map',
    kind: 'table',
    rowsPath: 'pauses.items',
    columns: [
      { key: 'lat', label: 'Lat' },
      { key: 'lon', label: 'Lon' },
      { key: 'label', label: 'Label' },
    ],
  },
  {
    id: 'climbs',
    title: 'Climbs',
    description: 'Montees detectees.',
    category: 'Climbs',
    kind: 'table',
    rowsPath: 'climbs.items',
    columns: [
      { key: 'distance_km', label: 'Distance', format: 'number', unit: 'km' },
      { key: 'elevation_gain_m', label: 'D+', format: 'meters', unit: 'm' },
      { key: 'avg_grade_percent', label: 'Pente moyenne', format: 'percent', unit: '%' },
      { key: 'pace_s_per_km', label: 'Allure', format: 'pace', unit: '/ km' },
      { key: 'vam_m_h', label: 'VAM', format: 'number', unit: 'm/h' },
      { key: 'start_idx', label: 'Start', format: 'integer' },
      { key: 'end_idx', label: 'End', format: 'integer' },
    ],
  },
  {
    id: 'performance-predictions',
    title: 'Predictions',
    description: 'Estimation des performances (Riegel).',
    category: 'Charts',
    kind: 'table',
    rowsPath: 'performance_predictions.items',
    columns: [
      { key: 'target_distance_km', label: 'Distance cible', format: 'number', unit: 'km' },
      { key: 'predicted_time_s', label: 'Temps estime', format: 'duration' },
      { key: 'base_distance_km', label: 'Base distance', format: 'number', unit: 'km' },
      { key: 'base_time_s', label: 'Base temps', format: 'duration' },
      { key: 'exponent', label: 'Exponent', format: 'number' },
    ],
  },
  {
    id: 'training-load',
    title: 'Training load',
    description: 'Charge interne (TRIMP).',
    category: 'Charts',
    kind: 'grid',
    gridColumns: 6,
    items: [
      { id: 'trimp', path: 'training_load.trimp', label: 'TRIMP', format: 'number' },
      { id: 'method', path: 'training_load.method', label: 'Methode', format: 'text' },
    ],
  },
  {
    id: 'series-index',
    title: 'Series index',
    description: 'Series disponibles (charts).',
    category: 'Series index',
    kind: 'table',
    hidden: true,
    rowsPath: 'series_index.available',
    columns: [
      { key: 'name', label: 'Serie' },
      { key: 'unit', label: 'Unite' },
      { key: 'x_axes', label: 'Axes' },
      { key: 'default', label: 'Default' },
    ],
  },
  {
    id: 'limits',
    title: 'Qualite / limites',
    description: 'Infos techniques sur les donnees retournees.',
    category: 'Limits',
    kind: 'grid',
    gridColumns: 6,
    items: [
      { id: 'downsampled', path: 'limits.downsampled', label: 'Downsampled', format: 'boolean' },
      { id: 'original_points', path: 'limits.original_points', label: 'Points originaux', format: 'integer' },
      { id: 'returned_points', path: 'limits.returned_points', label: 'Points retournes', format: 'integer' },
      { id: 'note', path: 'limits.note', label: 'Note', format: 'text' },
    ],
  },
];

export const THEORETICAL_METRIC_SECTIONS: MetricSection[] = [
  {
    id: 'theoretical-summary',
    title: 'Infos de course',
    description: 'Resume theorique.',
    category: 'Resume',
    kind: 'grid',
    gridColumns: 6,
    items: [
      { id: 'total_time_s', path: 'summary.total_time_s', label: 'Temps total', format: 'duration' },
      { id: 'total_distance_km', path: 'summary.total_distance_km', label: 'Distance', format: 'number', unit: 'km' },
      { id: 'average_pace_s_per_km', path: 'summary.average_pace_s_per_km', label: 'Allure moyenne', format: 'pace', unit: '/ km' },
      { id: 'elevation_gain_m', path: 'summary.elevation_gain_m', label: 'D+', format: 'meters', unit: 'm' },
    ],
  },
  {
    id: 'series-index',
    title: 'Series index',
    description: 'Series disponibles (charts).',
    category: 'Series index',
    kind: 'table',
    hidden: true,
    rowsPath: 'series_index.available',
    columns: [
      { key: 'name', label: 'Serie' },
      { key: 'unit', label: 'Unite' },
      { key: 'x_axes', label: 'Axes' },
      { key: 'default', label: 'Default' },
    ],
  },
  {
    id: 'limits',
    title: 'Qualite / limites',
    description: 'Infos techniques sur les donnees retournees.',
    category: 'Limits',
    kind: 'grid',
    gridColumns: 6,
    items: [
      { id: 'downsampled', path: 'limits.downsampled', label: 'Downsampled', format: 'boolean' },
      { id: 'original_points', path: 'limits.original_points', label: 'Points originaux', format: 'integer' },
      { id: 'note', path: 'limits.note', label: 'Note', format: 'text' },
    ],
  },
];

export const CHART_SERIES: ChartSeriesDefinition[] = [
  { name: 'pace', label: 'Allure', availability: 'both', format: 'pace', unit: '/ km' },
  { name: 'speed', label: 'Vitesse', availability: 'both', format: 'speed', unit: 'km/h' },
  { name: 'elevation', label: 'Elevation', availability: 'both', format: 'meters', unit: 'm' },
  { name: 'grade', label: 'Pente', availability: 'both', format: 'percent', unit: '%' },
  { name: 'moving', label: 'Moving', availability: 'both', format: 'number' },
  { name: 'heart_rate', label: 'Frequence cardiaque', availability: 'fit', format: 'integer', unit: 'bpm' },
  { name: 'cadence', label: 'Cadence', availability: 'cond', format: 'integer', unit: 'spm' },
  { name: 'power', label: 'Puissance', availability: 'fit', format: 'integer', unit: 'W' },
  { name: 'hr_zones', label: 'HR zones', availability: 'fit', format: 'number' },
  { name: 'power_zones', label: 'Power zones', availability: 'fit', format: 'number' },
];

export const SERIES_NAMES = CHART_SERIES.map((s) => s.name);

export const MAP_METRICS = [
  'bbox',
  'polyline',
  'markers[].lat',
  'markers[].lon',
  'markers[].label',
  'markers[].type',
];

export function getRegistryMetricPaths() {
  const paths = new Set<string>();
  const pushItem = (item: MetricItem) => paths.add(item.path);
  const pushColumnPaths = (section: MetricSection) => {
    if (!section.rowsPath || !section.columns) return;
    section.columns.forEach((col) => paths.add(`${section.rowsPath}[].${col.key}`));
  };

  KPI_METRICS.forEach(pushItem);
  ACTIVITY_LOAD_METRICS.forEach(pushItem);
  REAL_METRIC_SECTIONS.forEach((section) => {
    section.items?.forEach(pushItem);
    if (section.kind === 'table') pushColumnPaths(section);
    if (section.kind === 'list' && section.listPath) paths.add(`${section.listPath}[]`);
    if (section.kind === 'dataframe') {
      section.dataframes?.forEach((df) => {
        paths.add(df.path);
        df.columns?.forEach((col) => paths.add(`${df.path}.records[].${col}`));
      });
    }
  });

  THEORETICAL_METRIC_SECTIONS.forEach((section) => {
    section.items?.forEach(pushItem);
    if (section.kind === 'table') pushColumnPaths(section);
  });

  MAP_METRICS.forEach((metric) => paths.add(metric));
  SERIES_NAMES.forEach((name) => paths.add(`series.${name}`));

  return Array.from(paths);
}
