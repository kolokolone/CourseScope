import { formatPaceInputFromSeconds } from '@/lib/paceUtils';

export function computeDefaultPaceFromVma(vmaKmh?: number | null): string {
  if (typeof vmaKmh !== 'number' || !Number.isFinite(vmaKmh) || vmaKmh <= 0) {
    return '5:00';
  }
  const targetSpeedKmh = 0.75 * vmaKmh;
  if (!Number.isFinite(targetSpeedKmh) || targetSpeedKmh <= 0) {
    return '5:00';
  }
  const paceSecondsPerKm = 3600 / targetSpeedKmh;
  if (!Number.isFinite(paceSecondsPerKm) || paceSecondsPerKm <= 0) {
    return '5:00';
  }
  return formatPaceInputFromSeconds(Math.round(paceSecondsPerKm));
}
