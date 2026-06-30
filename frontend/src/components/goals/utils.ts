import { startOfDay, dateAtStart, formatDateLabel } from '@/lib/dateUtils';
import { formatDurationSeconds, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import type { GoalItem, GeoCityItem } from '@/types/api';

export const DAY_MS = 24 * 60 * 60 * 1000;

export function addDays(date: Date, count: number) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + count);
}

export function addWeeks(date: Date, count: number) {
  return addDays(date, count * 7);
}

export function isoDayKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export function mondayStartOfWeek(date: Date) {
  const start = startOfDay(date);
  const weekday = (start.getDay() + 6) % 7;
  return addDays(start, -weekday);
}

export function goalDaysDeltaFromToday(eventDate: string, today: Date) {
  const event = dateAtStart(eventDate);
  if (Number.isNaN(event.getTime())) return null;
  return Math.round((event.getTime() - today.getTime()) / DAY_MS);
}

export function goalCountdownLabel(goal: GoalItem, today: Date) {
  const delta = goalDaysDeltaFromToday(goal.event_date, today);
  if (delta === null) return '—';
  if (delta >= 0) return `J-${delta}`;
  return `J+${Math.abs(delta)}`;
}

export function monthWarmth(monthIndex: number) {
  const profile = [0.0, 0.05, 0.16, 0.32, 0.5, 0.75, 1.0, 0.96, 0.75, 0.48, 0.22, 0.08];
  return profile[monthIndex] ?? 0.5;
}

export function monthBackgroundStyle(date: Date): React.CSSProperties {
  const warmth = monthWarmth(date.getMonth());
  const cold = { r: 219, g: 234, b: 254 };
  const warm = { r: 255, g: 237, b: 213 };
  const mix = (a: number, b: number) => Math.round(a + (b - a) * warmth);
  return {
    backgroundColor: `rgba(${mix(cold.r, warm.r)}, ${mix(cold.g, warm.g)}, ${mix(cold.b, warm.b)}, 0.32)`,
  };
}

export function goalObjectiveLabel(goal: GoalItem) {
  if (typeof goal.target_time_s === 'number') return formatDurationSeconds(goal.target_time_s);
  if (typeof goal.target_pace_s_per_km === 'number') return `${formatPaceSecondsPerKm(goal.target_pace_s_per_km)} / km`;
  return '—';
}

export function compareGoals(a: GoalItem, b: GoalItem, key: SortKey) {
  if (key === 'name') return a.name.localeCompare(b.name, 'fr', { sensitivity: 'base' });
  if (key === 'date') return dateAtStart(a.event_date).getTime() - dateAtStart(b.event_date).getTime();
  if (key === 'distance') return a.distance_km - b.distance_km;
  if (key === 'location') return String(a.location ?? '').localeCompare(String(b.location ?? ''), 'fr', { sensitivity: 'base' });
  if (key === 'type') return a.race_type.localeCompare(b.race_type, 'fr', { sensitivity: 'base' });

  const aObjective = typeof a.target_time_s === 'number' ? a.target_time_s : a.target_pace_s_per_km ?? Number.POSITIVE_INFINITY;
  const bObjective = typeof b.target_time_s === 'number' ? b.target_time_s : b.target_pace_s_per_km ?? Number.POSITIVE_INFINITY;
  return aObjective - bObjective;
}

export type SortKey = 'name' | 'date' | 'distance' | 'location' | 'objective' | 'type';
export type SortDir = 'asc' | 'desc';
export type GoalMode = 'pace' | 'time';

export type GoalFormState = {
  name: string;
  eventDate: string;
  distanceKm: string;
  location: string;
  mode: GoalMode;
  targetPace: string;
  targetTime: string;
  raceType: 'road' | 'trail';
  notes: string;
};

export const INITIAL_FORM: GoalFormState = {
  name: '',
  eventDate: '',
  distanceKm: '',
  location: '',
  mode: 'time',
  targetPace: '5:00',
  targetTime: '01:00:00',
  raceType: 'road',
  notes: '',
};
