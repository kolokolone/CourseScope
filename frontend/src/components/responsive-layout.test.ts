import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

function source(relativePath: string) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf8');
}

describe('mobile responsive layout contract', () => {
  it('keeps the shared header compact without letting actions displace its title', () => {
    const shell = source('src/components/layout/AppShell.tsx');
    const header = source('src/components/layout/TopHeader.tsx');
    const actions = source('src/components/layout/HeaderActions.tsx');

    expect(shell).toContain('grid-cols-[minmax(0,1fr)]');
    expect(shell).toContain('min-h-0 min-w-0 flex-1 overflow-y-auto');
    expect(header).toContain('className="min-w-0 flex-1"');
    expect(header).toContain('text-xl font-semibold tracking-tight md:text-2xl');
    expect(actions).toContain('aria-label="Synchroniser avec Garmin"');
    expect(actions).toContain('className="hidden md:inline"');
  });

  it('provides mobile cards while preserving desktop tables for entity lists', () => {
    const activities = source('src/app/activities/page.tsx');
    const traces = source('src/app/traces/page.tsx');
    const goals = source('src/components/goals/GoalListTable.tsx');

    for (const file of [activities, traces, goals]) {
      expect(file).toContain('md:hidden');
      expect(file).toMatch(/hidden overflow-auto rounded-md border md:block/);
    }
    expect(activities).toContain('Trier par');
    expect(activities).toContain('data-testid="activities-mobile-sort-key"');
    expect(traces).toContain('Renommer');
    expect(goals).toContain('Modifier');
  });

  it('uses mobile rows for dense analysis data and restores the tables at md', () => {
    const activityPage = source('src/components/activity-beta/ActivityBetaPage.tsx');
    const splits = source('src/components/activity-beta/SplitsCard.tsx');
    const zones = source('src/components/activity-beta/ZonesCard.tsx');
    const stops = source('src/components/trace-planning/StopsEditor.tsx');

    expect(activityPage).toContain('grid-cols-[minmax(0,1fr)]');
    expect(activityPage).toContain('className="min-w-0 scroll-mt-28 xl:col-span-7"');
    expect(splits).toContain('className="space-y-2 md:hidden"');
    expect(splits).toContain('hidden overflow-x-auto px-2 md:block');
    expect(zones).toContain('className="space-y-2 md:hidden"');
    expect(zones).toContain('className="hidden w-full text-sm md:table"');
    expect(stops).toContain('className="space-y-3 md:hidden"');
    expect(stops).toContain('className="hidden overflow-x-auto rounded-lg border md:block"');
  });

  it('reduces analytical map and chart heights only below md', () => {
    const activityMap = source('src/components/activity-beta/SynchronizedActivityView.tsx');
    const activityChart = source('src/components/activity-beta/CompactAnalysisChart.tsx');
    const traceView = source('src/components/trace-planning/SynchronizedCourseView.tsx');
    const waterfall = source('src/components/charts/PaceHr3DChart.tsx');

    expect(activityMap).toContain('h-72 overflow-hidden');
    expect(activityMap).toContain('md:h-[420px] lg:h-[520px]');
    expect(activityChart).toContain('h-72 md:h-[500px]');
    expect(traceView).toContain('h-72 w-full md:h-[430px]');
    expect(waterfall).toContain('h-72 w-full min-w-0');
    expect(waterfall).toContain('md:h-[440px]');
  });
});
