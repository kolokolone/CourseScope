import type { RaceObjectiveType } from '@/types/api';

const PACE_PATTERN = /^(\d{1,2}):([0-5]\d)$/;
const DURATION_PATTERN = /^(\d{1,3}):([0-5]\d):([0-5]\d)$/;

export function formatPaceTarget(secondsPerKm: number): string {
  const seconds = Math.max(0, Math.round(secondsPerKm));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

export function parsePaceTarget(value: string): number | null {
  const match = PACE_PATTERN.exec(value.trim());
  if (!match) return null;
  return Number(match[1]) * 60 + Number(match[2]);
}

export function formatDurationTarget(totalSeconds: number): string {
  const seconds = Math.max(0, Math.round(totalSeconds));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

export function parseDurationTarget(value: string): number | null {
  const match = DURATION_PATTERN.exec(value.trim());
  if (!match) return null;
  return Number(match[1]) * 3600 + Number(match[2]) * 60 + Number(match[3]);
}

export function formatRaceTarget(type: RaceObjectiveType, value: number): string {
  if (type === 'pace') return formatPaceTarget(value);
  if (type === 'time') return formatDurationTarget(value);
  return String(Math.round(value * 10_000) / 100);
}

export function parseRaceTarget(type: RaceObjectiveType, value: string): number | null {
  if (type === 'pace') return parsePaceTarget(value);
  if (type === 'time') return parseDurationTarget(value);
  const percentage = Number(value.replace(',', '.'));
  return Number.isFinite(percentage) ? percentage / 100 : null;
}

export function defaultRaceTarget(type: RaceObjectiveType): string {
  if (type === 'pace') return '5:00';
  if (type === 'time') return '01:00:00';
  return '75';
}
