import type { ActivityMetadata } from '@/types/api';

type ActivityType = ActivityMetadata['activity_type'];

export function getActivityDetailPath(activityId: string, activityType: ActivityType) {
  return activityType === 'real' ? `/activities/${activityId}` : `/traces/${activityId}`;
}

export function getTraceDetailPath(traceId: string) {
  return `/traces/${traceId}`;
}
