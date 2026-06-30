'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ActivityUpload } from '@/components/upload/ActivityUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useActivityList } from '@/hooks/useActivity';
import { useGoalsList } from '@/hooks/useGoals';
import { usePersonalSettings } from '@/hooks/useSettings';
import { formatNumber } from '@/lib/metricsFormat';
import { getActivityDetailPath } from '@/lib/routes';
import { startOfDay, dateAtStart, formatDateLabel } from '@/lib/dateUtils';
import { Activity } from 'lucide-react';

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

  const handleUploadSuccess = (activityId: string, activityType: 'real' | 'theoretical') => {
    router.push(getActivityDetailPath(activityId, activityType));
  };

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
          activityType="real"
          title="Activite reelle"
          description="FIT ou GPX d'une activite courue (analyse reelle)."
          onUploadSuccess={handleUploadSuccess}
        />
        <ActivityUpload
          activityType="theoretical"
          title="Trace (theorique)"
          description="FIT ou GPX vierge pour une analyse theorique (pas d'auto-detection)."
          onUploadSuccess={handleUploadSuccess}
        />
      </div>

      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Historique d'activites
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
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="font-medium truncate">{activity.name || activity.filename}</div>
                        </div>
                        <div className="shrink-0 flex items-center gap-4 text-sm tabular-nums text-muted-foreground">
                          <div className="text-right">
                            {typeof dist === 'number' ? `${formatNumber(dist, { decimals: 1 })} km` : '—'}
                          </div>
                          <div className="text-right">{typeof elev === 'number' ? `D+ ${formatNumber(elev, { integer: true })} m` : '—'}</div>
                          <div className="text-right w-[5.5rem]">{dateLabel}</div>
                        </div>
                      </div>
                    </button>
                  );
                })}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {nextGoal && daysToNextGoal !== null ? (
          <Card className="w-full max-w-[20rem] self-start">
            <CardContent className="flex aspect-square flex-col items-center justify-center gap-4 p-5 text-center">
              <div className="text-sm text-muted-foreground">Prochain objectif dans :</div>
              <div className="text-5xl font-semibold tabular-nums tracking-tight">J-{daysToNextGoal}</div>
              <div className="w-full rounded-md border bg-background/60 p-3 text-left text-sm">
                <div className="font-semibold leading-tight">{nextGoal.name}</div>
                <div className="mt-1 text-muted-foreground">{formatDateLabel(nextGoal.event_date)}</div>
                <div className="mt-1 text-muted-foreground">
                  {`${formatNumber(nextGoal.distance_km, { decimals: 1 })} km • ${nextGoal.race_type === 'trail' ? 'Trail' : 'Course'}`}
                </div>
              </div>
            </CardContent>
          </Card>
        ) : null}

        <Card
          className="w-full max-w-[20rem] self-start"
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
