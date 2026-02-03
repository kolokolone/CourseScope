'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ActivityUpload } from '@/components/upload/ActivityUpload';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useActivityList, useCleanupActivities } from '@/hooks/useActivity';
import { formatDurationSeconds, formatNumber } from '@/lib/metricsFormat';
import { Activity, Trash2 } from 'lucide-react';

export default function HomePage() {
  const router = useRouter();
  const { data: activities, isLoading, refetch } = useActivityList();
  const cleanupMutation = useCleanupActivities();

  type TabId = 'upload' | 'activities';
  const [activeTab, setActiveTab] = React.useState<TabId>('upload');

  const handleUploadSuccess = (activityId: string, activityType: 'real' | 'theoretical') => {
    router.push(`/activity/${activityId}/${activityType}`);
  };

  const handleCleanup = async () => {
    if (window.confirm('Are you sure you want to delete all activities?')) {
      try {
        await cleanupMutation.mutateAsync();
        refetch();
      } catch {
        alert('Failed to cleanup activities');
      }
    }
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
              {activities && activities.activities.length > 0 ? (
                <Button variant="outline" size="sm" onClick={handleCleanup} disabled={cleanupMutation.isPending}>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Cleanup
                </Button>
              ) : null}
            </div>
          </div>
        </div>

        <div className="mt-3 overflow-x-auto">
          <div className="flex gap-2 whitespace-nowrap">
            <Button size="sm" variant={activeTab === 'upload' ? 'default' : 'outline'} onClick={() => setActiveTab('upload')}>
              Upload
            </Button>
            <Button
              size="sm"
              variant={activeTab === 'activities' ? 'default' : 'outline'}
              onClick={() => setActiveTab('activities')}
            >
              Activites
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        {activeTab === 'upload' ? (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div className="xl:col-span-2">
              <ActivityUpload onUploadSuccess={handleUploadSuccess} />
            </div>
            <Card>
              <CardHeader className="py-3 px-4">
                <CardTitle className="text-base flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  Raccourcis
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="text-sm text-muted-foreground">
                  Upload un fichier GPX/FIT puis ouvre l'analyse en 1 clic.
                </div>
                <div className="mt-3">
                  <Button size="sm" variant="outline" onClick={() => setActiveTab('activities')}>
                    Voir les activites
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : null}

        {activeTab === 'activities' ? (
          <Card>
            <CardHeader className="py-3 px-4">
              <div className="flex items-center justify-between gap-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  Activites recentes
                </CardTitle>
                <div className="text-xs text-muted-foreground tabular-nums">
                  {activities?.activities?.length ? `${activities.activities.length} items` : ''}
                </div>
              </div>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              {isLoading ? (
                <p className="text-muted-foreground">Loading activities...</p>
              ) : !activities || activities.activities.length === 0 ? (
                <div className="text-center py-8">
                  <Activity className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No activities uploaded yet</p>
                  <p className="text-sm text-gray-400 mt-2">Upload your first GPX or FIT file to get started</p>
                </div>
              ) : (
                <div className="max-h-[70vh] overflow-auto pr-1">
                  <div className="space-y-2">
                    {activities.activities.map((activity) => (
                      <div
                        key={activity.id}
                        className="p-3 border rounded-lg hover:bg-accent/30 cursor-pointer transition-colors"
                        onClick={() => router.push(`/activity/${activity.id}/${activity.activity_type}`)}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <h3 className="font-medium truncate max-w-xl">{activity.name || activity.filename}</h3>
                            <p className="text-sm text-muted-foreground">
                              {activity.activity_type} • {new Date(activity.created_at).toLocaleDateString()}
                            </p>
                          </div>
                          <div className="text-right shrink-0">
                            {activity.stats_sidebar.distance_km !== undefined ? (
                              <div className="font-medium tabular-nums">
                                {formatNumber(activity.stats_sidebar.distance_km, { decimals: 1 })} km
                              </div>
                            ) : null}
                            {activity.stats_sidebar.elapsed_time_s !== undefined ? (
                              <div className="text-sm text-muted-foreground tabular-nums">
                                {formatDurationSeconds(activity.stats_sidebar.elapsed_time_s)}
                              </div>
                            ) : null}
                            {activity.stats_sidebar.moving_time_s !== undefined ? (
                              <div className="text-xs text-muted-foreground tabular-nums">
                                En mouvement: {formatDurationSeconds(activity.stats_sidebar.moving_time_s)}
                              </div>
                            ) : null}
                            {activity.stats_sidebar.elevation_gain_m !== undefined ? (
                              <div className="text-xs text-muted-foreground tabular-nums">
                                D+: {formatNumber(activity.stats_sidebar.elevation_gain_m, { integer: true })} m
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
