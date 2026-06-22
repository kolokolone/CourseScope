'use client';

import { useState, useRef, useCallback } from 'react';
import { Pencil, Route, Clock, Gauge, Heart, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { HeroKpi } from './ui/HeroKpi';
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

  const gapText = isValidNumber(gap) ? formatPaceSecondsPerKm(gap as number) : null;

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {!isEditing ? (
            <>
              <h1 className="text-[28px] leading-[1.2] font-bold tracking-[-0.02em] text-slate-950 max-[720px]:text-[22px]">
                {activityName}
              </h1>
              <button onClick={handleStartEdit} className="text-slate-400 hover:text-slate-600" aria-label="Renommer">
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
          <Button variant="outline" size="sm" className="text-xs">Exporter</Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mt-2 text-sm text-slate-500">
        <span>{formatDateFR(activity?.started_at_utc)}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mt-[18px]">
        <HeroKpi icon={<Route className="h-4 w-4" />} label="Distance" value={isValidNumber(distance) ? formatNumber(distance as number) : 'Non disponible'} unit="km" />
        <HeroKpi icon={<Clock className="h-4 w-4" />} label="Temps total" value={isValidNumber(totalTime) ? formatDurationSeconds(totalTime as number) : 'Non disponible'} subValue={isValidNumber(movingTime) ? `${formatDurationSeconds(movingTime as number)} en mouvement` : undefined} />
        <HeroKpi icon={<Gauge className="h-4 w-4" />} label="Allure moyenne" value={isValidNumber(avgPace) ? formatPaceSecondsPerKm(avgPace as number) : 'Non disponible'} unit="/km" subValue={gapText ? `GAP ${gapText}/km` : undefined} />
        <HeroKpi icon={<Heart className="h-4 w-4" />} label="FC moyenne" value={isValidNumber(hrAvg) ? String(Math.round(hrAvg as number)) : 'Non disponible'} unit="bpm" />
        <HeroKpi icon={<Zap className="h-4 w-4" />} label="D+" value={isValidNumber(elevGain) ? String(Math.round(elevGain as number)) : 'Non disponible'} unit="m" />
      </div>
    </div>
  );
}
