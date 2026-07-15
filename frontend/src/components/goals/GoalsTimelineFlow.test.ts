import { describe, expect, it } from 'vitest';

import { connectorWidthFromDays } from './GoalsTimelineFlow';

describe('goals timeline spacing', () => {
  it('keeps time spacing progressive but compact', () => {
    expect(connectorWidthFromDays(1)).toBeLessThan(connectorWidthFromDays(30));
    expect(connectorWidthFromDays(30)).toBeLessThan(connectorWidthFromDays(210));
    expect(connectorWidthFromDays(1000)).toBe(connectorWidthFromDays(210));
  });
});
