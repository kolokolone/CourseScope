'use client';

import { useRouter } from 'next/navigation';
import { ActivityUpload } from '@/components/upload/ActivityUpload';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useActivityList, useCleanupActivities } from '@/hooks/useActivity';
import { Activity, Trash2 } from 'lucide-react';

export default function HomePage() {
  const router = useRouter();
  const { data: activities, isLoading, refetch } = useActivityList();
  const cleanupMutation = useCleanupActivities();

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
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">CourseScope</h1>
        <p className="text-lg text-gray-600">Upload and analyze your GPX/FIT activities</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <ActivityUpload onUploadSuccess={handleUploadSuccess} />
        </div>

        <div>
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Recent Activities
                </CardTitle>
                {activities && activities.activities.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCleanup}
                    disabled={cleanupMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Cleanup All
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <p className="text-gray-500">Loading activities...</p>
              ) : !activities || activities.activities.length === 0 ? (
                <div className="text-center py-8">
                  <Activity className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No activities uploaded yet</p>
                  <p className="text-sm text-gray-400 mt-2">
                    Upload your first GPX or FIT file to get started
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {activities.activities.map((activity) => (
                    <div
                      key={activity.id}
                      className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => router.push(`/activity/${activity.id}/${activity.activity_type}`)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-medium truncate max-w-xs">
                            {activity.name || activity.filename}
                          </h3>
                          <p className="text-sm text-gray-500">
                            {activity.activity_type} • {new Date(activity.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="text-right">
                          {activity.stats_sidebar.distance_km !== undefined && (
                            <p className="font-medium">
                              {activity.stats_sidebar.distance_km.toFixed(1)} km
                            </p>
                          )}
                          {activity.stats_sidebar.elapsed_time_s !== undefined && (
                            <p className="text-sm text-gray-500">
                              {Math.floor(activity.stats_sidebar.elapsed_time_s / 60)}m{' '}
                              {Math.floor(activity.stats_sidebar.elapsed_time_s % 60)}s
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
