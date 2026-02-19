import { describe, expect, it } from 'vitest';

import { getActivityDetailPath, getTraceDetailPath } from './routes';

describe('routes helpers', () => {
  it('routes real activities to /activities/[id]', () => {
    expect(getActivityDetailPath('real-123', 'real')).toBe('/activities/real-123');
  });

  it('routes theoretical activities to /traces/[id]', () => {
    expect(getActivityDetailPath('theo-123', 'theoretical')).toBe('/traces/theo-123');
  });

  it('routes traces to /traces/[id]', () => {
    expect(getTraceDetailPath('trace-123')).toBe('/traces/trace-123');
  });
});
