'use client';

import * as React from 'react';
import { Flag, Plus, Target } from 'lucide-react';

import { useCreateGoal, useDeleteGoal, useGoalsList, useUpdateGoal } from '@/hooks/useGoals';
import { GoalsTimelineFlow } from '@/components/goals/GoalsTimelineFlow';
import { GoalMiniCard } from '@/components/goals/GoalMiniCard';
import { GoalsObjectivesMap } from '@/components/goals/GoalsObjectivesMap';
import { CityAutocomplete } from '@/components/inputs/CityAutocomplete';
import { formatDurationSeconds, formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import type { GeoCityItem, GoalItem } from '@/types/api';
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

const DAY_MS = 24 * 60 * 60 * 1000;

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

function addDays(date: Date, count: number) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + count);
}

function addWeeks(date: Date, count: number) {
  return addDays(date, count * 7);
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

function isoDayKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function mondayStartOfWeek(date: Date) {
  const start = startOfDay(date);
  const weekday = (start.getDay() + 6) % 7;
  return addDays(start, -weekday);
}

function dateAtStart(eventDate: string) {
  return startOfDay(new Date(`${eventDate}T00:00:00`));
}

function goalDaysDeltaFromToday(eventDate: string, today: Date) {
  const event = dateAtStart(eventDate);
  if (Number.isNaN(event.getTime())) return null;
  return Math.round((event.getTime() - today.getTime()) / DAY_MS);
}

function goalCountdownLabel(goal: GoalItem, today: Date) {
  const delta = goalDaysDeltaFromToday(goal.event_date, today);
  if (delta === null) return '—';
  if (delta >= 0) return `J-${delta}`;
  return `J+${Math.abs(delta)}`;
}

function monthWarmth(monthIndex: number) {
  const profile = [0.0, 0.05, 0.16, 0.32, 0.5, 0.75, 1.0, 0.96, 0.75, 0.48, 0.22, 0.08];
  return profile[monthIndex] ?? 0.5;
}

function monthBackgroundStyle(date: Date): React.CSSProperties {
  const warmth = monthWarmth(date.getMonth());
  const cold = { r: 219, g: 234, b: 254 };
  const warm = { r: 255, g: 237, b: 213 };
  const mix = (a: number, b: number) => Math.round(a + (b - a) * warmth);
  return {
    backgroundColor: `rgba(${mix(cold.r, warm.r)}, ${mix(cold.g, warm.g)}, ${mix(cold.b, warm.b)}, 0.32)`,
  };
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

function Timeline({ goals, countdownByGoalId }: { goals: GoalItem[]; countdownByGoalId: Record<string, string> }) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-base">Ligne temporelle des objectifs</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <GoalsTimelineFlow goals={goals} countdownByGoalId={countdownByGoalId} />
      </CardContent>
    </Card>
  );
}

function GoalsCalendar({ goals }: { goals: GoalItem[] }) {
  const model = React.useMemo(() => {
    const today = startOfDay(new Date());
    const sortedDates = goals
      .map((goal) => dateAtStart(goal.event_date))
      .filter((d) => !Number.isNaN(d.getTime()))
      .sort((a, b) => a.getTime() - b.getTime());
    const lastDate = sortedDates.length > 0 ? sortedDates[sortedDates.length - 1] : today;
    const endAnchor = lastDate.getTime() < today.getTime() ? today : lastDate;
    const startWeek = mondayStartOfWeek(today);
    const endWeek = addDays(mondayStartOfWeek(endAnchor), 6);

    const byDay = new Map<string, GoalItem[]>();
    for (const goal of goals) {
      const key = String(goal.event_date).slice(0, 10);
      const bucket = byDay.get(key) ?? [];
      bucket.push(goal);
      byDay.set(key, bucket);
    }

    const weeks: Array<{
      key: string;
      days: Array<{ day: Date; goals: GoalItem[]; isPast: boolean; isToday: boolean }>;
      maxGoalsInDay: number;
    }> = [];

    for (let weekStart = startWeek; weekStart.getTime() <= endWeek.getTime(); weekStart = addWeeks(weekStart, 1)) {
      const days = Array.from({ length: 7 }, (_, offset) => {
        const day = addDays(weekStart, offset);
        const dayKey = isoDayKey(day);
        const dayGoals = byDay.get(dayKey) ?? [];
        return {
          day,
          goals: dayGoals,
          isPast: day.getTime() < today.getTime(),
          isToday: day.getTime() === today.getTime(),
        };
      });

      const maxGoalsInDay = Math.max(0, ...days.map((day) => day.goals.length));
      weeks.push({
        key: isoDayKey(weekStart),
        days,
        maxGoalsInDay,
      });
      if (weeks.length > 52) break;
    }

    return {
      weeks,
      weekLabels: ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
    };
  }, [goals]);

  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-base">Calendrier des objectifs</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <div className="overflow-auto rounded-md border border-slate-200/80 text-xs text-muted-foreground">
          <div className="grid grid-cols-7">
            {model.weekLabels.map((label) => (
              <div key={label} className="border-b border-r border-slate-200/80 bg-slate-50/70 px-2 py-1 font-medium last:border-r-0">
                {label}
              </div>
            ))}
          </div>

          {model.weeks.map((week) => {
            const rowHeightClass = week.maxGoalsInDay === 0 ? 'min-h-[2.5rem]' : week.maxGoalsInDay === 1 ? 'min-h-[7rem]' : 'min-h-[9.75rem]';
            return (
              <div key={week.key} className={`grid grid-cols-7 ${rowHeightClass}`}>
                {week.days.map((cell, idx) => {
                  const hasGoals = cell.goals.length > 0;
                  const bgClass = hasGoals ? 'bg-primary/10' : cell.isPast ? 'bg-muted/60' : '';
                  const style = hasGoals || cell.isPast ? undefined : monthBackgroundStyle(cell.day);
                  return (
                    <div
                      key={`${week.key}-${idx}`}
                      className={`flex h-full flex-col border-r border-b border-slate-200/80 p-1.5 ${idx === 6 ? 'border-r-0' : ''} ${bgClass} ${cell.isToday ? 'ring-1 ring-inset ring-primary/40' : ''}`}
                      style={style}
                    >
                      <div className="mb-1 text-[11px] text-slate-600 tabular-nums">{cell.day.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}</div>
                      {hasGoals ? (
                        <div className="space-y-1">
                          {cell.goals.map((goal) => (
                            <GoalMiniCard key={goal.id} goal={goal} className="w-full" />
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            );
          })}
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
  const [selectedCity, setSelectedCity] = React.useState<GeoCityItem | null>(null);
  const [locationNeedsSelection, setLocationNeedsSelection] = React.useState(false);

  const [sortKey, setSortKey] = React.useState<SortKey>('date');
  const [sortDir, setSortDir] = React.useState<SortDir>('asc');

  const goals = React.useMemo(() => goalsQuery.data?.goals ?? [], [goalsQuery.data?.goals]);
  const hasGoals = goals.length > 0;
  const isSubmitting = createGoal.isPending || updateGoal.isPending;

  const resetFormState = React.useCallback(() => {
    setEditingGoalId(null);
    setForm(INITIAL_FORM);
    setFormError(null);
    setSelectedCity(null);
    setLocationNeedsSelection(false);
  }, []);

  const sortedGoals = React.useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1;
    return goals.slice().sort((a, b) => compareGoals(a, b, sortKey) * dir);
  }, [goals, sortDir, sortKey]);

  const today = React.useMemo(() => startOfDay(new Date()), []);
  const countdownByGoalId = React.useMemo(
    () =>
      Object.fromEntries(
        goals.map((goal) => [goal.id, goalCountdownLabel(goal, today)])
      ) as Record<string, string>,
    [goals, today]
  );

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
    setSelectedCity(
      goal.location_city && goal.location_country && typeof goal.location_lat === 'number' && typeof goal.location_lon === 'number'
        ? {
            label: goal.location ?? `${goal.location_city}, ${goal.location_country}`,
            city: goal.location_city,
            country: goal.location_country,
            country_code: goal.location_country_code ?? null,
            lat: goal.location_lat,
            lon: goal.location_lon,
          }
        : null
    );
    setLocationNeedsSelection(false);
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
      location_city?: string;
      location_country?: string;
      location_country_code?: string;
      location_lat?: number;
      location_lon?: number;
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
    if (location && locationNeedsSelection && selectedCity === null) {
      setFormError('Selectionne une ville dans la liste de suggestions.');
      return;
    }
    if (location) payload.location = location;
    if (selectedCity) {
      payload.location_city = selectedCity.city;
      payload.location_country = selectedCity.country;
      payload.location_country_code = selectedCity.country_code ?? undefined;
      payload.location_lat = selectedCity.lat;
      payload.location_lon = selectedCity.lon;
    }
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
        location_city: string | null;
        location_country: string | null;
        location_country_code: string | null;
        location_lat: number | null;
        location_lon: number | null;
        target_time_s: number | null;
        target_pace_s_per_km: number | null;
        race_type: 'road' | 'trail';
        notes: string | null;
      } = {
        name,
        event_date: eventDate,
        distance_km: distanceKm,
        location: location || null,
        location_city: selectedCity?.city ?? null,
        location_country: selectedCity?.country ?? null,
        location_country_code: selectedCity?.country_code ?? null,
        location_lat: selectedCity?.lat ?? null,
        location_lon: selectedCity?.lon ?? null,
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

  const goalFormCard = isFormOpen ? (
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
              <CityAutocomplete
                className="h-9 w-full rounded-md border px-3"
                value={form.location}
                onChange={(next) => {
                  setForm((prev) => ({ ...prev, location: next }));
                  setLocationNeedsSelection(next.trim().length > 0);
                }}
                onSelectionChange={(item) => {
                  setSelectedCity(item);
                  setLocationNeedsSelection(item === null && form.location.trim().length > 0);
                }}
                placeholder="Ville, Pays"
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
  ) : null;

  return (
    <div className="space-y-4">
      {!hasGoals ? (
        <Card>
          <CardContent className="py-12">
            <div className="mx-auto flex max-w-lg flex-col items-center gap-3 text-center">
              <div className="relative h-14 w-14 text-slate-400">
                <Target className="h-14 w-14" />
                <div className="absolute left-1/2 top-1/2 h-[3px] w-14 -translate-x-1/2 -translate-y-1/2 rotate-[-35deg] rounded-full bg-slate-500/70" />
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
          <Timeline goals={goals} countdownByGoalId={countdownByGoalId} />
          {goalFormCard}
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
                        <th className="px-3 py-2 text-left font-medium">Dans :</th>
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
                          <td className="px-3 py-2 tabular-nums">{goalCountdownLabel(goal, today)}</td>
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

          <GoalsCalendar goals={goals} />

          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-base">Map des objectifs</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <GoalsObjectivesMap goals={goals} />
            </CardContent>
          </Card>

        </>
      )}

      {!hasGoals ? goalFormCard : null}
    </div>
  );
}
