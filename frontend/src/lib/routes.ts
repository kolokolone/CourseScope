import type { ActivityId, ActivityMetadata, TraceId } from '@/types/api';

type ActivityType = ActivityMetadata['activity_type'];

export function getActivityDetailPath(activityId: ActivityId, activityType: ActivityType) {
  return `/activities/${activityId}`;
}

export function getTraceDetailPath(traceId: TraceId) {
  return `/traces/${traceId}`;
}
