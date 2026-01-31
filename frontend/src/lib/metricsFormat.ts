export type MetricFormat =
  | 'number'
  | 'integer'
  | 'duration'
  | 'pace'
  | 'speed'
  | 'meters'
  | 'percent'
  | 'text'
  | 'boolean';

const DURATION_METRIC_KEYS = new Set([
  'total_time_s',
  'moving_time_s',
  'pause_time_s',
  'longest_pause_s',
]);

function pad2(value: number) {
  return String(value).padStart(2, '0');
}

function toWholeSeconds(value: number) {
  return Math.round(value);
}

export function isDurationMetricKey(key: string) {
  return DURATION_METRIC_KEYS.has(key);
}

export function isPaceMetricKey(key: string) {
  return key.endsWith('_s_per_km');
}

export function isDeltaMetricKey(key: string) {
  return key.includes('delta');
}

export function formatDurationSeconds(rawSeconds: number) {
  if (!Number.isFinite(rawSeconds)) return String(rawSeconds);

  const sign = rawSeconds < 0 ? '-' : '';
  const totalSeconds = toWholeSeconds(Math.abs(rawSeconds));

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${sign}${hours}:${pad2(minutes)}:${pad2(seconds)}`;
  }

  const totalMinutes = Math.floor(totalSeconds / 60);
  return `${sign}${pad2(totalMinutes)}:${pad2(seconds)}`;
}

export function formatPaceSecondsPerKm(
  rawSecondsPerKm: number,
  options?: {
    forceSign?: boolean;
  }
) {
  if (!Number.isFinite(rawSecondsPerKm)) return String(rawSecondsPerKm);

  const absSeconds = Math.abs(rawSecondsPerKm);
  const totalSeconds = toWholeSeconds(absSeconds);

  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  const sign = rawSecondsPerKm < 0 ? '-' : options?.forceSign && rawSecondsPerKm > 0 ? '+' : '';
  return `${sign}${pad2(minutes)}:${pad2(seconds)}`;
}

export function formatNumber(value: number, options?: { decimals?: number; integer?: boolean }) {
  if (!Number.isFinite(value)) return String(value);
  if (options?.integer) return String(Math.round(value));
  const decimals = options?.decimals ?? (Number.isInteger(value) ? 0 : 2);
  return value.toFixed(decimals);
}

export function formatSpeedKmh(value: number) {
  return formatNumber(value, { decimals: 1 });
}

export function formatMeters(value: number) {
  return formatNumber(value, { integer: true });
}

export function formatPercent(value: number) {
  return formatNumber(value, { decimals: 1 });
}

export function formatMetricValue(value: unknown, format: MetricFormat) {
  if (value === null || value === undefined) {
    return format === 'text' ? '' : '';
  }

  if (format === 'text') {
    return String(value);
  }

  if (format === 'boolean') {
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'number') return value !== 0 ? 'Yes' : 'No';
    return String(value);
  }

  if (typeof value !== 'number') {
    return String(value);
  }

  switch (format) {
    case 'duration':
      return formatDurationSeconds(value);
    case 'pace':
      return formatPaceSecondsPerKm(value);
    case 'speed':
      return formatSpeedKmh(value);
    case 'meters':
      return formatMeters(value);
    case 'percent':
      return formatPercent(value);
    case 'integer':
      return formatNumber(value, { integer: true });
    case 'number':
      return formatNumber(value);
    default:
      return formatNumber(value);
  }
}
