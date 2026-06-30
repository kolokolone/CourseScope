'use client';

import { useState, useRef, useCallback } from 'react';
import { ArrowLeft, Pencil } from 'lucide-react';
import { useRouter } from 'next/navigation';
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
  const router = useRouter();
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
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
      <button
        onClick={() => router.push('/activities')}
        className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors mb-4"
      >
        <ArrowLeft className="h-4 w-4" />
        Retour aux activités
      </button>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          {!isEditing ? (
            <>
              <h1 className="text-[28px] leading-[1.2] font-bold tracking-[-0.02em] text-slate-950 max-[720px]:text-[22px] truncate">
                {activityName}
              </h1>
              <button onClick={handleStartEdit} className="text-slate-400 hover:text-slate-600 shrink-0" aria-label="Renommer">
                <Pencil className="h-4 w-4" />
              </button>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                className="h-9 rounded-md border border-slate-200 px-3 text-base font-semibold"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <Button size="sm" onClick={handleSave}>Enregistrer</Button>
              <Button size="sm" variant="ghost" onClick={handleCancel}>Annuler</Button>
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

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mt-[18px]">
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
  );
}
