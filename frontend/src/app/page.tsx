'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ActivityUpload } from '@/components/upload/ActivityUpload';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useActivityList } from '@/hooks/useActivity';
import { useGoalsList } from '@/hooks/useGoals';
import { formatNumber } from '@/lib/metricsFormat';
import { getActivityDetailPath } from '@/lib/routes';
import { Activity, TrendingUp } from 'lucide-react';

function startOfDay(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function dateAtStart(eventDate: string) {
  return startOfDay(new Date(`${eventDate}T00:00:00`));
}

function formatDateLabel(eventDate: string) {
  const date = dateAtStart(eventDate);
  if (Number.isNaN(date.getTime())) return eventDate;
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function HomePage() {
  const router = useRouter();
  const { data: activities, isLoading } = useActivityList();
  const goalsQuery = useGoalsList();

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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_auto]">
        <Card>
          <CardHeader className="py-3 px-4">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Historique d'activites
              </CardTitle>
              <div className="flex gap-2">
                <Button asChild size="sm" variant="outline">
                  <Link href="/activities">Afficher toutes les activites</Link>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href="/progress">
                    <TrendingUp className="h-4 w-4 mr-2" />
                    Progression
                  </Link>
                </Button>
              </div>
            </div>
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
      </div>
    </div>
  );
}
