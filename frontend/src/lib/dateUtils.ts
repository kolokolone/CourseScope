/**
 * Shared date utilities for CourseScope frontend.
 */

export type HistoryRange = '3m' | '6m' | '1y' | 'all';

/** Returns a new Date at 00:00:00 local time. */
export function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

/** Parses YYYY-MM-DD to Date at 00:00:00 local time. */
export function dateAtStart(eventDate: string): Date {
  const d = new Date(`${eventDate}T00:00:00`);
  return startOfDay(d);
}

/**
 * Formats a date for display.
 * Accepts ISO date string (YYYY-MM-DD) or millisecond timestamp.
 */
export function formatDateLabel(date: string | number): string {
  if (typeof date === 'number') {
    const d = new Date(date);
    if (!Number.isFinite(d.getTime())) return '—';
    return d.toLocaleDateString();
  }
  const d = new Date(`${date}T00:00:00`);
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

/** Returns a date-only ISO string (YYYY-MM-DD) in UTC. */
export function isoDateUtc(d: Date): string {
  const dt = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  return dt.toISOString().slice(0, 10);
}

/** Returns the Monday 00:00 UTC of the week containing the given date. */
export function weekStartUtc(date: Date): Date {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const day = d.getUTCDay();
  const diff = (day + 6) % 7;
  d.setUTCDate(d.getUTCDate() - diff);
  return d;
}

/** Shifts range start backward based on selected range. */
export function shiftRangeStart(end: Date, range: HistoryRange): Date {
  if (range === 'all') return new Date(0);
  const d = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate()));
  if (range === '3m') d.setUTCMonth(d.getUTCMonth() - 3);
  if (range === '6m') d.setUTCMonth(d.getUTCMonth() - 6);
  if (range === '1y') d.setUTCFullYear(d.getUTCFullYear() - 1);
  return d;
}
