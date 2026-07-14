import { describe, expect, it } from 'vitest';

import { getActivityDetailPath, getTraceDetailPath } from './routes';
import { asActivityId, asTraceId } from '@/types/api';

describe('routes helpers', () => {
  it('routes real activities to /activities/[id]', () => {
    expect(getActivityDetailPath(asActivityId('real-123'), 'real')).toBe('/activities/real-123');
  });

  it('never routes an activity id to a trace page', () => {
    expect(getActivityDetailPath(asActivityId('activity-123'), 'real')).toBe('/activities/activity-123');
  });

  it('routes traces to /traces/[id]', () => {
    expect(getTraceDetailPath(asTraceId('trace-123'))).toBe('/traces/trace-123');
  });
});
