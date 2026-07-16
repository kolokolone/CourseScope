'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ActivityUpload } from '@/components/upload/ActivityUpload';
import { TraceUpload } from '@/components/upload/TraceUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { goalObjectiveLabel } from '@/components/goals/utils';
import { useActivityList } from '@/hooks/useActivity';
import { useGoalsList } from '@/hooks/useGoals';
import { usePersonalSettings } from '@/hooks/useSettings';
import { formatNumber } from '@/lib/metricsFormat';
import { getActivityDetailPath, getTraceDetailPath } from '@/lib/routes';
import type { ActivityId, TraceId } from '@/types/api';
import { startOfDay, dateAtStart, formatDateLabel } from '@/lib/dateUtils';
import { Activity, ArrowRight, CalendarDays, Flag, MapPin, Route } from 'lucide-react';

export default function HomePage() {
  const router = useRouter();
  const { data: activities, isLoading } = useActivityList();
  const goalsQuery = useGoalsList();
  const personalSettingsQuery = usePersonalSettings();

  const nextGoal = React.useMemo(() => {
    const today = startOfDay(new Date());
    const goals = goalsQuery.data?.goals ?? [];
    return goals
      .filter((goal) => {
        const d = dateAtStart(goal.event_date);
        return !Number.isNaN(d.getTime()) && d.getTime() >= today.getTime();
      })
      .sort((a, b) => dateAtStart(a.event_date).getTime() - dateAtStart(b.event_date).getTime())[0];
  }, [goalsQuery.data?.goals]);

  const daysToNextGoal = React.useMemo(() => {
    if (!nextGoal) return null;
    const today = startOfDay(new Date());
    const eventDate = dateAtStart(nextGoal.event_date);
    const deltaMs = eventDate.getTime() - today.getTime();
    const dayMs = 24 * 3600 * 1000;
    return Math.max(0, Math.ceil(deltaMs / dayMs));
  }, [nextGoal]);

  const handleActivityUploadSuccess = (activityId: ActivityId) => router.push(getActivityDetailPath(activityId, 'real'));
  const handleTraceUploadSuccess = (traceId: TraceId) => router.push(getTraceDetailPath(traceId));

  const activitySortEpoch = (a: { started_at?: string | null; created_at: string }) => {
    const raw = a.started_at ?? a.created_at;
    const t = new Date(raw).getTime();
    return Number.isFinite(t) ? t : 0;
  };

  const vo2maxCurrent = React.useMemo(() => {
    const value = personalSettingsQuery.data?.vo2max_lastest;
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
  }, [personalSettingsQuery.data?.vo2max_lastest]);

  const vo2Category = React.useMemo(() => {
    if (vo2maxCurrent === null) return { label: 'Non disponible', color: '#94a3b8' };
    if (vo2maxCurrent >= 54.0) return { label: 'Superieur', color: '#8b5cf6' };
    if (vo2maxCurrent >= 48.3) return { label: 'Excellent', color: '#2563eb' };
    if (vo2maxCurrent >= 44.0) return { label: 'Bon', color: '#16a34a' };
    if (vo2maxCurrent >= 40.5) return { label: 'Passable', color: '#f59e0b' };
    return { label: 'Mauvais', color: '#dc2626' };
  }, [vo2maxCurrent]);

  const vo2PointStyle = React.useMemo(() => {
    if (vo2maxCurrent === null) return { left: '50%', top: '10%' };
    const min = 30;
    const max = 62;
    const ratio = Math.min(1, Math.max(0, (vo2maxCurrent - min) / (max - min)));
    const angle = -140 + ratio * 280;
    const rad = (angle * Math.PI) / 180;
    const radius = 58;
    const center = 70;
    const x = center + Math.sin(rad) * radius;
    const y = center - Math.cos(rad) * radius;
    return { left: `${x}px`, top: `${y}px` };
  }, [vo2maxCurrent]);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ActivityUpload
          title="Activite reelle"
          description="FIT ou GPX d'une activite courue (analyse reelle)."
          onUploadSuccess={handleActivityUploadSuccess}
        />
        <TraceUpload
          title="Trace theorique"
          description="GPX ou FIT pour preparer une course, sans creation d'activite."
          onUploadSuccess={handleTraceUploadSuccess}
        />
      </div>

      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Historique des activités
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {isLoading ? (
            <p className="text-muted-foreground">Loading activities...</p>
          ) : !activities || activities.activities.length === 0 ? (
            <div className="text-center py-8">
              <Activity className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Aucune activite enregistree</p>
              <p className="text-sm text-gray-400 mt-2">Upload un fichier pour lancer une analyse.</p>
            </div>
          ) : (
            <div className="divide-y rounded-md border">
              {activities.activities
                .slice()
                .sort((a, b) => activitySortEpoch(b) - activitySortEpoch(a))
                .slice(0, 10)
                .map((activity) => {
                  const dateLabel = new Date(activity.started_at ?? activity.created_at).toLocaleDateString();
                  const dist = activity.stats_sidebar.distance_km;
                  const elev = activity.stats_sidebar.elevation_gain_m;
                  return (
                    <button
                      key={activity.id}
                      type="button"
                      className="w-full px-3 py-2 text-left hover:bg-accent/30 transition-colors"
                      onClick={() => router.push(getActivityDetailPath(activity.id, activity.activity_type))}
                    >
                      <div className="flex min-w-0 flex-col gap-2 md:flex-row md:items-center md:justify-between md:gap-3">
                        <div className="min-w-0">
                          <div className="break-words font-medium md:truncate" title={activity.name || activity.filename}>{activity.name || activity.filename}</div>
                        </div>
                        <div className="grid w-full grid-cols-2 gap-x-3 gap-y-1 text-sm tabular-nums text-muted-foreground md:flex md:w-auto md:shrink-0 md:items-center md:gap-4">
                          <div className="text-right">
                            {typeof dist === 'number' ? `${formatNumber(dist, { decimals: 1 })} km` : '—'}
                          </div>
                          <div className="text-right">{typeof elev === 'number' ? `D+ ${formatNumber(elev, { integer: true })} m` : '—'}</div>
                          <div className="col-span-2 md:w-[5.5rem] md:text-right">{dateLabel}</div>
                        </div>
                      </div>
                    </button>
                  );
                })}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        {nextGoal && daysToNextGoal !== null ? (
          <Card className="relative w-full overflow-hidden self-stretch">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-br from-primary/12 via-primary/5 to-transparent" />
            <CardContent className="relative flex h-full min-h-80 flex-col p-5 md:p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                    <Flag className="h-4 w-4" /> Prochain objectif
                  </div>
                  <h2 className="mt-3 break-words text-2xl font-semibold tracking-tight">{nextGoal.name}</h2>
                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1.5"><CalendarDays className="h-4 w-4" />{formatDateLabel(nextGoal.event_date)}</span>
                    {nextGoal.location ? <span className="flex items-center gap-1.5"><MapPin className="h-4 w-4" />{nextGoal.location}</span> : null}
                  </div>
                </div>
                <div className="rounded-2xl border border-primary/20 bg-card/90 px-4 py-3 text-center shadow-sm">
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Échéance</div>
                  <div className="mt-0.5 text-3xl font-semibold tabular-nums text-primary">J-{daysToNextGoal}</div>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
                {[
                  { label: 'Distance', value: `${formatNumber(nextGoal.distance_km, { decimals: 1 })} km` },
                  { label: 'Terrain', value: nextGoal.race_type === 'trail' ? 'Trail' : 'Course' },
                  { label: 'Objectif', value: goalObjectiveLabel(nextGoal) },
                ].map((item) => (
                  <div key={item.label} className="rounded-xl border border-border bg-card/70 p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{item.label}</div>
                    <div className="mt-1 font-semibold tabular-nums">{item.value}</div>
                  </div>
                ))}
              </div>

              <div className="mt-auto flex flex-col items-stretch justify-between gap-4 pt-6 md:flex-row md:items-end">
                <div className="flex items-center gap-2 text-sm text-muted-foreground"><Route className="h-4 w-4" />Préparer l&apos;échéance et suivre les objectifs.</div>
                <Button className="w-full md:w-auto" variant="outline" size="sm" onClick={() => router.push('/goals')}>
                  Voir les objectifs <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        <Card
          className="mx-auto w-full max-w-[20rem] self-start md:mx-0"
          title="Superieur: 54.0+ (violet) | Excellent: 48.3-54.0 (bleu) | Bon: 44.0-48.3 (vert) | Passable: 40.5-44.0 (orange) | Mauvais: <40.5 (rouge)"
        >
          <CardContent className="flex aspect-square flex-col items-center justify-center gap-4 p-5 text-center">
            <div className="text-sm text-muted-foreground">VO2 max actuelle</div>
            <div className="relative h-[140px] w-[140px]">
              <div
                className="absolute inset-0 rounded-full"
                style={{
                  background:
                    'conic-gradient(from -140deg, #dc2626 0deg 56deg, #f59e0b 56deg 112deg, #16a34a 112deg 168deg, #2563eb 168deg 224deg, #8b5cf6 224deg 280deg, #e2e8f0 280deg 360deg)',
                }}
              />
              <div className="absolute inset-[12px] rounded-full bg-background" />
              <div className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-slate-900" style={vo2PointStyle} />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-5xl font-semibold tabular-nums tracking-tight">{vo2maxCurrent === null ? '—' : formatNumber(vo2maxCurrent, { decimals: 1 })}</div>
              </div>
            </div>
            <div className="text-sm font-medium" style={{ color: vo2Category.color }}>
              {vo2Category.label}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
