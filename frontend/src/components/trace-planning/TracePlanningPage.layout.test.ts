import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

function source(relativePath: string) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf8');
}

describe('trace planning layout', () => {
  it('uses one synchronized pace chart below a full-width map', () => {
    const synchronized = source('src/components/trace-planning/SynchronizedCourseView.tsx');
    const distributions = source('src/components/trace-planning/PlanningCharts.tsx');

    expect(synchronized).toContain('height="430px"');
    expect(synchronized).toContain('heightClassName="h-[215px]"');
    expect(synchronized).toContain('Allure vs distance');
    expect(synchronized).toContain('<TheoreticalPaceElevationChart');
    expect(distributions).not.toContain('TheoreticalPaceElevationChart');
  });

  it('places both histogram cards before collapsible splits', () => {
    const page = source('src/components/trace-planning/TracePlanningPage.tsx');
    const distributionsIndex = page.indexOf('<PlanningCharts preview={preview} />');
    const splitsIndex = page.indexOf('id="decoupage"');

    expect(distributionsIndex).toBeGreaterThan(0);
    expect(splitsIndex).toBeGreaterThan(distributionsIndex);
    expect(page).toContain('Splits kilométriques ({preview.splits.length})');
    expect(page).not.toContain('Creer le plan principal');
    expect(page).not.toContain('Créer le plan principal');
  });
});
