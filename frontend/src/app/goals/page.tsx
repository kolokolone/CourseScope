'use client';

import * as React from 'react';
import { CircleOff, Flag, Plus, Target } from 'lucide-react';

import { useCreateGoal, useDeleteGoal, useGoalsList, useUpdateGoal } from '@/hooks/useGoals';
import { formatDurationSeconds, formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import type { GoalItem } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type SortKey = 'name' | 'date' | 'distance' | 'location' | 'objective' | 'type';
type SortDir = 'asc' | 'desc';
type GoalMode = 'pace' | 'time';

type GoalFormState = {
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

const INITIAL_FORM: GoalFormState = {
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

function startOfDay(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function addMonths(date: Date, count: number) {
  return new Date(date.getFullYear(), date.getMonth() + count, date.getDate());
}

function parseFlexibleSeconds(input: string): number | null {
  const raw = input.trim();
  if (!raw) return null;
  if (/^\d+$/.test(raw)) {
    const minutes = Number(raw);
    if (!Number.isFinite(minutes) || minutes <= 0) return null;
    return minutes * 60;
  }
  const parts = raw.split(':').map((p) => p.trim());
  if (!parts.every((p) => /^\d+$/.test(p))) return null;
  if (parts.length === 2) {
    const mm = Number(parts[0]);
    const ss = Number(parts[1]);
    if (ss >= 60) return null;
    return mm * 60 + ss;
  }
  if (parts.length === 3) {
    const hh = Number(parts[0]);
    const mm = Number(parts[1]);
    const ss = Number(parts[2]);
    if (mm >= 60 || ss >= 60) return null;
    return hh * 3600 + mm * 60 + ss;
  }
  return null;
}

function formatPaceInputFromSeconds(value: number): string {
  const total = Math.max(0, Math.round(value));
  const mm = Math.floor(total / 60);
  const ss = total % 60;
  return `${mm}:${String(ss).padStart(2, '0')}`;
}

function formatTimeInputFromSeconds(value: number): string {
  const total = Math.max(0, Math.round(value));
  const hh = Math.floor(total / 3600);
  const mm = Math.floor((total % 3600) / 60);
  const ss = total % 60;
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
}

function formatDateLabel(eventDate: string) {
  const date = new Date(`${eventDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return eventDate;
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatMonthLabel(date: Date) {
  return date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
}

function dateAtStart(eventDate: string) {
  return startOfDay(new Date(`${eventDate}T00:00:00`));
}

function goalObjectiveLabel(goal: GoalItem) {
  if (typeof goal.target_time_s === 'number') return formatDurationSeconds(goal.target_time_s);
  if (typeof goal.target_pace_s_per_km === 'number') return `${formatPaceSecondsPerKm(goal.target_pace_s_per_km)} / km`;
  return '—';
}

function compareGoals(a: GoalItem, b: GoalItem, key: SortKey) {
  if (key === 'name') return a.name.localeCompare(b.name, 'fr', { sensitivity: 'base' });
  if (key === 'date') return dateAtStart(a.event_date).getTime() - dateAtStart(b.event_date).getTime();
  if (key === 'distance') return a.distance_km - b.distance_km;
  if (key === 'location') return String(a.location ?? '').localeCompare(String(b.location ?? ''), 'fr', { sensitivity: 'base' });
  if (key === 'type') return a.race_type.localeCompare(b.race_type, 'fr', { sensitivity: 'base' });

  const aObjective = typeof a.target_time_s === 'number' ? a.target_time_s : a.target_pace_s_per_km ?? Number.POSITIVE_INFINITY;
  const bObjective = typeof b.target_time_s === 'number' ? b.target_time_s : b.target_pace_s_per_km ?? Number.POSITIVE_INFINITY;
  return aObjective - bObjective;
}

function Timeline({ goals }: { goals: GoalItem[] }) {
  const sorted = React.useMemo(
    () => goals.slice().sort((a, b) => dateAtStart(a.event_date).getTime() - dateAtStart(b.event_date).getTime()),
    [goals]
  );

  const model = React.useMemo(() => {
    const today = startOfDay(new Date());
    const dates = sorted.map((goal) => dateAtStart(goal.event_date)).filter((d) => !Number.isNaN(d.getTime()));
    const lastDate = dates.length > 0 ? dates[dates.length - 1] : today;
    const end = addMonths(lastDate, 1);
    const spanMs = Math.max(1, end.getTime() - today.getTime());

    const positionedEvents = sorted.map((goal) => {
      const date = dateAtStart(goal.event_date);
      const pos = Math.max(0, Math.min(1, (date.getTime() - today.getTime()) / spanMs));
      const shade = Math.round(78 - pos * 38);
      const stroke = `hsl(213 94% ${Math.max(30, Math.min(78, shade))}%)`;
      return { goal, pos, stroke };
    });

    let previousPos = -1;
    let previousLane = 1;
    const events = positionedEvents.map((event) => {
      const isDense = previousPos >= 0 && event.pos - previousPos < 0.08;
      const lane: 0 | 1 = isDense ? (previousLane === 0 ? 1 : 0) : 0;
      previousPos = event.pos;
      previousLane = lane;
      return {
        ...event,
        lane,
      };
    });

    const monthBoundaries: number[] = [];
    const cursor = new Date(today.getFullYear(), today.getMonth() + 1, 1);
    while (cursor.getTime() < end.getTime()) {
      monthBoundaries.push(Math.max(0, Math.min(1, (cursor.getTime() - today.getTime()) / spanMs)));
      cursor.setMonth(cursor.getMonth() + 1, 1);
    }

    const segmentDates = [today, ...monthBoundaries.map((p) => new Date(today.getTime() + p * spanMs)), end];
    const segmentCenters = segmentDates.slice(0, -1).map((start, idx) => {
      const stop = segmentDates[idx + 1];
      const center = (start.getTime() + stop.getTime()) / 2;
      const pos = Math.max(0, Math.min(1, (center - today.getTime()) / spanMs));
      return { pos, label: formatMonthLabel(start) };
    });

    const firstUpcoming = dates.find((d) => d.getTime() >= today.getTime()) ?? null;
    const daysLeft = firstUpcoming ? Math.ceil((firstUpcoming.getTime() - today.getTime()) / (24 * 3600 * 1000)) : null;
    const firstPos = firstUpcoming ? Math.max(0, Math.min(1, (firstUpcoming.getTime() - today.getTime()) / spanMs)) : null;

    return {
      events,
      monthBoundaries,
      segmentCenters,
      daysLeft,
      firstPos,
      hasMonthTicks: monthBoundaries.length > 0,
      minWidthPx: Math.max(780, 680 + sorted.length * 90),
    };
  }, [sorted]);

  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-base">Ligne temporelle des objectifs</CardTitle>
      </CardHeader>
      <CardContent className="px-2 pb-4">
        <div className="overflow-x-auto">
          <div className="mx-2" style={{ minWidth: `${model.minWidthPx}px` }}>
            <div className="relative h-[320px]">
              <div className="absolute inset-x-4 top-0 h-[320px]">
                <div className="absolute left-0 right-0 top-[150px] h-1 rounded-full bg-slate-300" />
                <div className="absolute left-0 top-[150px] -translate-x-1/2 -translate-y-1/2">
                  <div className="h-3.5 w-3.5 rounded-full border-2 border-slate-500 bg-white" />
                </div>
                <div className="absolute -right-2 top-[141px] text-slate-500">→</div>

                {model.hasMonthTicks
                  ? model.monthBoundaries.map((pos, idx) => (
                      <div
                        key={`month-tick-${idx}`}
                        className="absolute top-[26px] h-[248px] w-px bg-slate-200/70"
                        style={{ left: `${pos * 100}%` }}
                      />
                    ))
                  : null}

                {model.daysLeft !== null && model.firstPos !== null && model.daysLeft >= 0 && model.firstPos > 0 ? (
                  <>
                    <div
                      className="absolute top-[150px] h-0 border-t-2 border-dashed border-slate-500/65"
                      style={{ left: 0, width: `${model.firstPos * 100}%` }}
                    />
                    <div
                      className="absolute top-[132px] -translate-x-1/2 rounded-full border bg-white px-2 py-0.5 text-xs font-semibold text-slate-700"
                      style={{ left: `${(model.firstPos / 2) * 100}%` }}
                    >
                      {`J-${model.daysLeft}`}
                    </div>
                  </>
                ) : null}

                {model.events.map(({ goal, pos, stroke, lane }) => {
                  const isTop = lane === 0;
                  return (
                    <div key={goal.id} className="absolute -translate-x-1/2" style={{ left: `${pos * 100}%` }}>
                      {isTop ? (
                        <>
                          <div className="absolute left-1/2 top-[66px] h-[84px] -translate-x-1/2 border-l-2 border-dashed" style={{ borderColor: stroke }} />
                          <div className="absolute left-1/2 top-2 w-44 -translate-x-1/2 rounded-md border bg-white/95 p-2 text-[11px] shadow-sm">
                            <div className="font-semibold leading-tight">{goal.name}</div>
                            <div className="text-slate-600">{formatDateLabel(goal.event_date)}</div>
                            <div className="text-slate-600">{`${formatNumber(goal.distance_km, { decimals: 1 })} km • ${goal.race_type === 'trail' ? 'Trail' : 'Course'}`}</div>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="absolute left-1/2 top-[150px] h-[44px] -translate-x-1/2 border-l-2 border-dashed" style={{ borderColor: stroke }} />
                          <div className="absolute left-1/2 top-[194px] w-44 -translate-x-1/2 rounded-md border bg-white/95 p-2 text-[11px] shadow-sm">
                            <div className="font-semibold leading-tight">{goal.name}</div>
                            <div className="text-slate-600">{formatDateLabel(goal.event_date)}</div>
                            <div className="text-slate-600">{`${formatNumber(goal.distance_km, { decimals: 1 })} km • ${goal.race_type === 'trail' ? 'Trail' : 'Course'}`}</div>
                          </div>
                        </>
                      )}
                      <div className="absolute left-1/2 top-[146px] h-2.5 w-2.5 -translate-x-1/2 rounded-full border-2 bg-white" style={{ borderColor: stroke }} />
                    </div>
                  );
                })}

                {model.segmentCenters.map(({ pos, label }, idx) => (
                  <div
                    key={`month-label-${idx}`}
                    className="absolute top-[286px] -translate-x-1/2 text-xs text-slate-600"
                    style={{ left: `${pos * 100}%` }}
                  >
                    {label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function GoalsPage() {
  const goalsQuery = useGoalsList();
  const createGoal = useCreateGoal();
  const deleteGoal = useDeleteGoal();
  const updateGoal = useUpdateGoal();

  const [isFormOpen, setIsFormOpen] = React.useState(false);
  const [editingGoalId, setEditingGoalId] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<GoalFormState>(INITIAL_FORM);
  const [formError, setFormError] = React.useState<string | null>(null);

  const [sortKey, setSortKey] = React.useState<SortKey>('date');
  const [sortDir, setSortDir] = React.useState<SortDir>('asc');

  const goals = goalsQuery.data?.goals ?? [];
  const hasGoals = goals.length > 0;
  const isSubmitting = createGoal.isPending || updateGoal.isPending;

  const resetFormState = React.useCallback(() => {
    setEditingGoalId(null);
    setForm(INITIAL_FORM);
    setFormError(null);
  }, []);

  const sortedGoals = React.useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1;
    return goals.slice().sort((a, b) => compareGoals(a, b, sortKey) * dir);
  }, [goals, sortDir, sortKey]);

  const toggleSort = (key: SortKey) => {
    setSortKey((prev) => {
      if (prev !== key) {
        setSortDir(key === 'date' ? 'asc' : 'asc');
        return key;
      }
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      return prev;
    });
  };

  const startEditingGoal = React.useCallback((goal: GoalItem) => {
    const isTimeGoal = typeof goal.target_time_s === 'number' && Number.isFinite(goal.target_time_s);
    const targetTime = isTimeGoal ? formatTimeInputFromSeconds(goal.target_time_s as number) : '01:00:00';
    const paceSeconds = typeof goal.target_pace_s_per_km === 'number' && Number.isFinite(goal.target_pace_s_per_km) ? goal.target_pace_s_per_km : 300;

    setForm({
      name: goal.name,
      eventDate: String(goal.event_date).slice(0, 10),
      distanceKm: String(goal.distance_km),
      location: goal.location ?? '',
      mode: isTimeGoal ? 'time' : 'pace',
      targetPace: formatPaceInputFromSeconds(paceSeconds),
      targetTime,
      raceType: goal.race_type,
      notes: goal.notes ?? '',
    });
    setEditingGoalId(goal.id);
    setFormError(null);
    setIsFormOpen(true);
  }, []);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    const name = form.name.trim();
    const eventDate = form.eventDate.trim();
    const distanceKm = Number(form.distanceKm);
    if (!name) {
      setFormError('Le nom de la course est requis.');
      return;
    }
    if (!eventDate) {
      setFormError('La date est requise.');
      return;
    }
    if (!Number.isFinite(distanceKm) || distanceKm <= 0) {
      setFormError('La distance doit être un nombre > 0.');
      return;
    }

    const payload: {
      name: string;
      event_date: string;
      distance_km: number;
      location?: string;
      target_time_s?: number;
      target_pace_s_per_km?: number;
      race_type: 'road' | 'trail';
      notes?: string;
    } = {
      name,
      event_date: eventDate,
      distance_km: distanceKm,
      race_type: form.raceType,
    };

    const location = form.location.trim();
    if (location) payload.location = location;
    const notes = form.notes.trim();
    if (notes) payload.notes = notes;

    if (form.mode === 'time') {
      const seconds = parseFlexibleSeconds(form.targetTime);
      if (seconds === null || seconds <= 0) {
        setFormError('Temps objectif invalide (format hh:mm:ss, mm:ss ou minutes).');
        return;
      }
      payload.target_time_s = seconds;
    } else {
      const seconds = parseFlexibleSeconds(form.targetPace);
      if (seconds === null || seconds < 120 || seconds > 1200) {
        setFormError('Allure objectif invalide (entre 2:00 et 20:00 /km).');
        return;
      }
      payload.target_pace_s_per_km = seconds;
    }

    if (editingGoalId) {
      const updatePayload: {
        name: string;
        event_date: string;
        distance_km: number;
        location: string | null;
        target_time_s: number | null;
        target_pace_s_per_km: number | null;
        race_type: 'road' | 'trail';
        notes: string | null;
      } = {
        name,
        event_date: eventDate,
        distance_km: distanceKm,
        location: location || null,
        target_time_s: form.mode === 'time' ? payload.target_time_s ?? null : null,
        target_pace_s_per_km: form.mode === 'pace' ? payload.target_pace_s_per_km ?? null : null,
        race_type: form.raceType,
        notes: notes || null,
      };
      await updateGoal.mutateAsync({ goalId: editingGoalId, payload: updatePayload });
    } else {
      await createGoal.mutateAsync(payload);
    }

    resetFormState();
    setIsFormOpen(false);
  };

  return (
    <div className="space-y-4">
      {!hasGoals ? (
        <Card>
          <CardContent className="py-12">
            <div className="mx-auto flex max-w-lg flex-col items-center gap-3 text-center">
              <div className="relative h-14 w-14 text-slate-400">
                <Target className="h-14 w-14" />
                <CircleOff className="absolute -right-1 -top-1 h-7 w-7" />
              </div>
              <div className="text-lg font-semibold">Pas d&apos;objectifs enregistré encore</div>
              <div className="text-sm text-muted-foreground">Ajoute ton premier objectif de course ou trail pour démarrer ton suivi.</div>
              <Button
                onClick={() => {
                  resetFormState();
                  setIsFormOpen(true);
                }}
              >
                Enregistrer son premier objectif
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <Timeline goals={goals} />
          <Card>
            <CardHeader className="py-3 px-4">
              <div className="flex items-center justify-between gap-3">
                <CardTitle className="text-base">Liste des objectifs</CardTitle>
                <Button
                  size="sm"
                  onClick={() => {
                    if (isFormOpen && editingGoalId === null) {
                      setIsFormOpen(false);
                      return;
                    }
                    resetFormState();
                    setIsFormOpen(true);
                  }}
                >
                  <Plus className="mr-1 h-4 w-4" />
                  Ajouter un nouvel objectif
                </Button>
              </div>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              {goalsQuery.isLoading ? (
                <div className="text-muted-foreground">Chargement...</div>
              ) : (
                <div className="overflow-auto rounded-md border">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/40">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium">
                          <button type="button" className="hover:underline" onClick={() => toggleSort('name')}>
                            Nom
                          </button>
                        </th>
                        <th className="px-3 py-2 text-left font-medium">
                          <button type="button" className="hover:underline" onClick={() => toggleSort('date')}>
                            Date
                          </button>
                        </th>
                        <th className="px-3 py-2 text-right font-medium">
                          <button type="button" className="hover:underline" onClick={() => toggleSort('distance')}>
                            Distance (km)
                          </button>
                        </th>
                        <th className="px-3 py-2 text-left font-medium">
                          <button type="button" className="hover:underline" onClick={() => toggleSort('location')}>
                            Localisation
                          </button>
                        </th>
                        <th className="px-3 py-2 text-left font-medium">
                          <button type="button" className="hover:underline" onClick={() => toggleSort('objective')}>
                            Objectif
                          </button>
                        </th>
                        <th className="px-3 py-2 text-left font-medium">
                          <button type="button" className="hover:underline" onClick={() => toggleSort('type')}>
                            Type
                          </button>
                        </th>
                        <th className="px-3 py-2 text-right font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {sortedGoals.map((goal) => (
                        <tr key={goal.id}>
                          <td className="px-3 py-2 font-medium">{goal.name}</td>
                          <td className="px-3 py-2">{formatDateLabel(goal.event_date)}</td>
                          <td className="px-3 py-2 text-right tabular-nums">{formatNumber(goal.distance_km, { decimals: 1 })}</td>
                          <td className="px-3 py-2">{goal.location || '—'}</td>
                          <td className="px-3 py-2 tabular-nums">{goalObjectiveLabel(goal)}</td>
                          <td className="px-3 py-2">{goal.race_type === 'trail' ? 'Trail' : 'Course à pied'}</td>
                          <td className="px-3 py-2 text-right">
                            <div className="flex justify-end gap-2">
                              <Button size="sm" variant="outline" onClick={() => startEditingGoal(goal)}>
                                Modifier
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={async () => {
                                  await deleteGoal.mutateAsync(goal.id);
                                }}
                                disabled={deleteGoal.isPending}
                              >
                                Supprimer
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {isFormOpen ? (
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-base flex items-center gap-2">
              <Flag className="h-4 w-4" />
              {editingGoalId ? 'Modifier un objectif' : 'Nouvel objectif'}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                <label className="text-sm">
                  <div className="text-muted-foreground">Nom</div>
                  <input
                    className="mt-1 h-9 w-full rounded-md border px-3"
                    value={form.name}
                    onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder="Marathon de Paris"
                  />
                </label>

                <label className="text-sm">
                  <div className="text-muted-foreground">Date</div>
                  <input
                    type="date"
                    className="mt-1 h-9 w-full rounded-md border px-3"
                    value={form.eventDate}
                    onChange={(e) => setForm((prev) => ({ ...prev, eventDate: e.target.value }))}
                  />
                </label>

                <label className="text-sm">
                  <div className="text-muted-foreground">Distance (km)</div>
                  <input
                    type="number"
                    step="0.1"
                    className="mt-1 h-9 w-full rounded-md border px-3"
                    value={form.distanceKm}
                    onChange={(e) => setForm((prev) => ({ ...prev, distanceKm: e.target.value }))}
                    placeholder="42.2"
                  />
                </label>

                <label className="text-sm">
                  <div className="text-muted-foreground">Localisation</div>
                  <input
                    className="mt-1 h-9 w-full rounded-md border px-3"
                    value={form.location}
                    onChange={(e) => setForm((prev) => ({ ...prev, location: e.target.value }))}
                    placeholder="Paris"
                  />
                </label>
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                <label className="text-sm">
                  <div className="text-muted-foreground">Type de course</div>
                  <select
                    className="mt-1 h-9 w-full rounded-md border bg-background px-3"
                    value={form.raceType}
                    onChange={(e) => setForm((prev) => ({ ...prev, raceType: e.target.value as 'road' | 'trail' }))}
                  >
                    <option value="road">Course à pied</option>
                    <option value="trail">Trail</option>
                  </select>
                </label>

                <label className="text-sm">
                  <div className="text-muted-foreground">Objectif principal</div>
                  <select
                    className="mt-1 h-9 w-full rounded-md border bg-background px-3"
                    value={form.mode}
                    onChange={(e) => setForm((prev) => ({ ...prev, mode: e.target.value as GoalMode }))}
                  >
                    <option value="time">Temps cible</option>
                    <option value="pace">Allure cible</option>
                  </select>
                </label>

                {form.mode === 'time' ? (
                  <label className="text-sm md:col-span-2 xl:col-span-2">
                    <div className="text-muted-foreground">Temps cible</div>
                    <input
                      className="mt-1 h-9 w-full rounded-md border px-3"
                      value={form.targetTime}
                      onChange={(e) => setForm((prev) => ({ ...prev, targetTime: e.target.value }))}
                      placeholder="03:30:00"
                    />
                  </label>
                ) : (
                  <label className="text-sm md:col-span-2 xl:col-span-2">
                    <div className="text-muted-foreground">Allure cible (/km)</div>
                    <input
                      className="mt-1 h-9 w-full rounded-md border px-3"
                      value={form.targetPace}
                      onChange={(e) => setForm((prev) => ({ ...prev, targetPace: e.target.value }))}
                      placeholder="4:45"
                    />
                  </label>
                )}
              </div>

              <label className="block text-sm">
                <div className="text-muted-foreground">Notes (optionnel)</div>
                <textarea
                  className="mt-1 min-h-20 w-full rounded-md border px-3 py-2"
                  value={form.notes}
                  onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))}
                  placeholder="Plan nutrition, stratégie de course, etc."
                />
              </label>

              {formError ? <div className="text-sm text-red-600">{formError}</div> : null}

              <div className="flex flex-wrap items-center justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setIsFormOpen(false);
                    resetFormState();
                  }}
                >
                  Annuler
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Enregistrement...' : editingGoalId ? 'Enregistrer les modifications' : 'Enregistrer l’objectif'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
