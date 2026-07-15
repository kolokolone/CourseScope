import type { RaceStopType } from '@/types/api';

export const RACE_STOP_LABELS: Record<RaceStopType, string> = {
  water: 'Eau',
  nutrition: 'Alimentation',
  water_nutrition: 'Eau et alimentation',
  assistance: 'Assistance',
  other: 'Autre',
};

export const RACE_STOP_ICONS: Record<RaceStopType, string> = {
  water: '💧',
  nutrition: '🍌',
  water_nutrition: '💧🍌',
  assistance: '🛠️',
  other: '●',
};

export function formatStopDurationInput(seconds: number): string {
  const safe = Math.max(0, Math.round(Number.isFinite(seconds) ? seconds : 0));
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, '0')}`;
}

export function parseStopDurationInput(value: string): number | null {
  const match = value.trim().match(/^(\d+):([0-5]\d)$/);
  if (!match) return null;
  return Number(match[1]) * 60 + Number(match[2]);
}
