'use client';

import { useState, useRef, useCallback } from 'react';
import { Activity, Pencil } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRenameActivity } from '@/hooks/useActivity';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { formatDurationSeconds, formatPaceSecondsPerKm, formatNumber } from '@/lib/metricsFormat';
import { isValidNumber } from './utils/formatters';
import type { RealActivityResponse } from '@/types/api';

type ActivityBetaHeroProps = {
  activity: RealActivityResponse;
  activityId: string;
};

function formatDateFR(iso: string | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return '';
  return d.toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'long', year: 'numeric',
  });
}

function formatPace(v: number): string {
  return formatPaceSecondsPerKm(v);
}

function HeroKpiCard({ label, value, unit, sub }: { label: string; value: string; unit?: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className="mt-2 flex items-baseline gap-1 tabular-nums">
        <span className="text-2xl font-semibold text-slate-950">{value}</span>
        {unit && <span className="text-sm text-slate-500">{unit}</span>}
      </div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

export function ActivityBetaHero({ activity, activityId }: ActivityBetaHeroProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const renameMutation = useRenameActivity();

  const activityName = activity?.activity_name || `Activité ${activityId}`;
  const distance = getValueAtPath(activity, 'summary.distance_km');
  const totalTime = getValueAtPath(activity, 'summary.total_time_s');
  const movingTime = getValueAtPath(activity, 'summary.moving_time_s');
  const avgPace = getValueAtPath(activity, 'summary.average_pace_s_per_km');
  const hrAvg = getValueAtPath(activity, 'summary.cardio.hr_avg_bpm');
  const elevGain = getValueAtPath(activity, 'summary.elevation_gain_m') ?? getValueAtPath(activity, 'garmin_summary.elevation_gain_m');
  const gap = getValueAtPath(activity, 'garmin_summary.gap_mean_s_per_km');
  const hrMax = getValueAtPath(activity, 'garmin_summary.hr_max_bpm') ?? getValueAtPath(activity, 'summary.cardio.hr_max_bpm');
  const power = getValueAtPath(activity, 'power.mean_w');
  const cadence = getValueAtPath(activity, 'cadence.mean_spm');

  const activityType = getValueAtPath(activity, 'activity_type') as string | undefined;
  const source = getValueAtPath(activity, 'source') as string | undefined;

  const handleStartEdit = useCallback(() => {
    setDraft(activityName);
    setIsEditing(true);
    setTimeout(() => inputRef.current?.select(), 0);
  }, [activityName]);

  const handleSave = useCallback(() => {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== activityName) {
      renameMutation.mutate({ activityId, name: trimmed });
    }
    setIsEditing(false);
  }, [draft, activityName, activityId, renameMutation]);

  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setDraft('');
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') handleCancel();
  }, [handleSave, handleCancel]);

  const gapText = isValidNumber(gap) ? formatPace(gap as number) : null;

  return (
    <section className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
      <div className="bg-gradient-to-br from-primary/10 via-background to-emerald-500/10 p-5 sm:p-7">
      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-primary">
        <Activity className="h-4 w-4" />Analyse d&apos;activité
      </div>

      <div className="flex min-w-0 items-center justify-between">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {!isEditing ? (
            <>
              <h1 className="min-w-0 truncate text-[22px] font-bold leading-[1.2] tracking-[-0.02em] text-slate-950 md:text-[28px]" title={activityName}>
                {activityName}
              </h1>
              <button onClick={handleStartEdit} className="text-slate-400 hover:text-slate-600 shrink-0" aria-label="Renommer">
                <Pencil className="h-4 w-4" />
              </button>
            </>
          ) : (
            <div className="flex min-w-0 flex-1 flex-col items-stretch gap-2 md:flex-row md:items-center">
              <input
                ref={inputRef}
                className="h-9 w-full min-w-0 rounded-md border border-slate-200 px-3 text-base font-semibold"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <div className="grid grid-cols-2 gap-2 md:flex md:items-center">
                <Button size="sm" onClick={handleSave}>Enregistrer</Button>
                <Button size="sm" variant="ghost" onClick={handleCancel}>Annuler</Button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mt-2 text-sm text-slate-500">
        <span>{formatDateFR(activity?.started_at_utc)}</span>
        {source && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-inset ring-slate-200">
            {source}
          </span>
        )}
        {activityType && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-inset ring-slate-200">
            {activityType}
          </span>
        )}
      </div>

      <div className="mt-[18px] grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <HeroKpiCard label="Distance" value={isValidNumber(distance) ? formatNumber(distance as number) : 'Non disponible'} unit="km" />
        <HeroKpiCard label="Temps total" value={isValidNumber(totalTime) ? formatDurationSeconds(totalTime as number) : 'Non disponible'} sub={isValidNumber(movingTime) ? `${formatDurationSeconds(movingTime as number)} en mouvement` : undefined} />
        <HeroKpiCard label="Allure moyenne" value={isValidNumber(avgPace) ? formatPace(avgPace as number) : 'Non disponible'} unit="/km" sub={gapText ? `GAP ${gapText}` : undefined} />
        <HeroKpiCard label="FC moyenne" value={isValidNumber(hrAvg) ? String(Math.round(hrAvg as number)) : 'Non disponible'} unit="bpm" sub={isValidNumber(hrMax) ? `Max ${Math.round(hrMax as number)}` : undefined} />
        <HeroKpiCard label="D+" value={isValidNumber(elevGain) ? String(Math.round(elevGain as number)) : 'Non disponible'} unit="m" />
        {isValidNumber(power) ? (
          <HeroKpiCard label="Puissance moyenne" value={String(Math.round(power as number))} unit="W" />
        ) : isValidNumber(cadence) ? (
          <HeroKpiCard label="Cadence moyenne" value={String(Math.round(cadence as number))} unit="spm" />
        ) : null}
      </div>
      </div>
    </section>
  );
}
