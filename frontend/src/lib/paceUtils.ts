/**
 * Utility functions for pace formatting and calculations
 */

export function secToMmSs(totalSeconds: number): string {
  const n = Number(totalSeconds);
  if (!Number.isFinite(n)) return '--';
  const clamped = Math.max(0, Math.floor(n));
  const minutes = Math.floor(clamped / 60);
  const seconds = clamped % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

export const formatPace = (paceSec: number): string => {
  return secToMmSs(paceSec);
};

function clamp01(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

/**
 * Pace -> blue ramp.
 * - Faster (smaller s/km) -> lighter blue
 * - Slower (bigger s/km) -> darker blue
 *
 * Caller provides min/max for normalization.
 */
export function paceToBlue(
  paceSec: number,
  minPaceSec: number,
  maxPaceSec: number,
  options?: {
    hue?: number;
    saturation?: number;
    lightnessFast?: number;
    lightnessSlow?: number;
    fallback?: string;
    invert?: boolean;
  }
) {
  const fallback = options?.fallback ?? 'hsl(210, 90%, 55%)';
  if (!Number.isFinite(paceSec) || !Number.isFinite(minPaceSec) || !Number.isFinite(maxPaceSec)) return fallback;

  const range = maxPaceSec - minPaceSec;
  if (range <= 0) return fallback;

  // t=0 -> fastest (min), t=1 -> slowest (max)
  const t = clamp01((paceSec - minPaceSec) / range);
  const hue = options?.hue ?? 210;
  const saturation = options?.saturation ?? 88;
  const invert = Boolean(options?.invert);
  // Default ramp:
  // - non-inverted: faster -> lighter, slower -> darker
  // - inverted: faster -> darker, slower -> lighter
  const defaultFast = invert ? 42 : 74;
  const defaultSlow = invert ? 74 : 42;
  const lightnessFast = options?.lightnessFast ?? defaultFast;
  const lightnessSlow = options?.lightnessSlow ?? defaultSlow;

  const lightness = lightnessFast + (lightnessSlow - lightnessFast) * t;
  return `hsl(${hue}, ${saturation}%, ${Math.round(lightness)}%)`;
}

export const paceToSeconds = (paceStr: string): number => {
  if (!paceStr || paceStr === '--') {
    return 0;
  }
  
  const parts = paceStr.split(':');
  if (parts.length !== 2) {
    return 0;
  }
  
  const minutes = parseInt(parts[0], 10);
  const seconds = parseInt(parts[1], 10);
  return minutes * 60 + seconds;
};

/**
 * Calculate pace normalization for bar widths and colors
 * Faster pace = lower seconds per km = longer bar + lighter color
 */
export const calculatePaceMetrics = (paceValues: number[]) => {
  const validPaces = paceValues.filter(p => p !== null && p !== undefined && !isNaN(p)) as number[];
  
  if (validPaces.length === 0) {
    return {
      minPace: 0,
      maxPace: 0,
      paceRange: 0,
      normalizedWidths: paceValues.map(() => 0.5),
      colors: paceValues.map(() => '#56B4E9')
    };
  }
  
  const minPace = Math.min(...validPaces);
  const maxPace = Math.max(...validPaces);
  const paceRange = maxPace - minPace;
  
  const normalizedWidths = validPaces.map(pace => {
    if (paceRange === 0) return 0.7;
    return Math.max(0.2, (maxPace - pace) / paceRange);
  });
  
  // Color calculation: lighter = faster (smaller pace value)
  const colors = validPaces.map((pace) => paceToBlue(pace, minPace, maxPace, { fallback: '#56B4E9' }));
  
  return {
    minPace,
    maxPace,
    paceRange,
    normalizedWidths,
    colors
  };
};
