'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ActivityUpload } from '@/components/upload/ActivityUpload';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useActivityList } from '@/hooks/useActivity';
import { formatNumber } from '@/lib/metricsFormat';
import { Activity, Settings, TrendingUp } from 'lucide-react';

const PERSIST_UPLOADS_KEY = 'coursescope.persist_uploads_to_disk';

function getPersistUploadsDefaultOff() {
  if (typeof window === 'undefined') return false;
  const raw = window.localStorage.getItem(PERSIST_UPLOADS_KEY);
  if (raw === null) return false;
  return raw === 'true';
}

export default function HomePage() {
  const router = useRouter();
  const { data: activities, isLoading } = useActivityList();

  const [persistUploadsToDisk, setPersistUploadsToDisk] = React.useState(false);
  React.useEffect(() => {
    setPersistUploadsToDisk(getPersistUploadsDefaultOff());
  }, []);

  const handleUploadSuccess = (activityId: string, activityType: 'real' | 'theoretical') => {
    router.push(`/activity/${activityId}/${activityType}`);
  };

  const activitySortEpoch = (a: { started_at?: string | null; created_at: string }) => {
    const raw = a.started_at ?? a.created_at;
    const t = new Date(raw).getTime();
    return Number.isFinite(t) ? t : 0;
  };

  return (
    <div className="container mx-auto py-6 px-4 max-w-6xl">
      <div className="sticky top-0 z-40 -mx-4 px-4 pb-3 bg-background/90 backdrop-blur border-b">
        <div className="pt-2">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-xs text-muted-foreground">CourseScope</div>
              <h1 className="text-2xl font-bold truncate">Analyse</h1>
              <div className="text-xs text-muted-foreground truncate">Upload et exploration des activites</div>
            </div>
            <div className="flex gap-2">
              <Button asChild variant="outline" size="sm">
                <Link href="/progress">
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Progression
                </Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/settings">
                  <Settings className="h-4 w-4 mr-2" />
                  Parametres
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ActivityUpload
            activityType="real"
            title="Activite reelle"
            description="FIT ou GPX d'une activite courue (analyse reelle)."
            onUploadSuccess={handleUploadSuccess}
            persistToDisk={persistUploadsToDisk}
          />
          <ActivityUpload
            activityType="theoretical"
            title="Trace (theorique)"
            description="FIT ou GPX vierge pour une analyse theorique (pas d'auto-detection)."
            onUploadSuccess={handleUploadSuccess}
            persistToDisk={persistUploadsToDisk}
          />
        </div>

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
                <p className="text-sm text-gray-400 mt-2">Upload un fichier puis active l'enregistrement si besoin.</p>
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
                        onClick={() => router.push(`/activity/${activity.id}/${activity.activity_type}`)}
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
      </div>
    </div>
  );
}
