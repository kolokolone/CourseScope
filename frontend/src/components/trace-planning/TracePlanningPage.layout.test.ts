import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

function source(relativePath: string) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf8');
}

describe('trace planning layout', () => {
  it('uses one synchronized pace chart below a full-width map', () => {
    const synchronized = source('src/components/trace-planning/SynchronizedCourseView.tsx');
    const fullscreen = source('src/components/trace-planning/FullscreenCourseView.tsx');
    const page = source('src/components/trace-planning/TracePlanningPage.tsx');
    const distributions = source('src/components/trace-planning/PlanningCharts.tsx');

    expect(synchronized).toContain('height="430px"');
    expect(synchronized).toContain('heightClassName="h-[430px]"');
    expect(synchronized).toContain('Allure vs distance');
    expect(synchronized).toContain('<TheoreticalPaceElevationChart');
    expect(synchronized).toContain('<FullscreenCourseView');
    expect(fullscreen).toContain('role="dialog"');
    expect(fullscreen).toContain('<RacePassageTimeline passages={timeline} />');
    expect(page).toContain('aria-label="Afficher la carte en plein écran"');
    expect(page).toContain('timeline={preview.timeline_passages ?? []}');
    expect(distributions).not.toContain('TheoreticalPaceElevationChart');
  });

  it('adds the optional stop name before the existing stop fields', () => {
    const editor = source('src/components/trace-planning/StopsEditor.tsx');
    expect(editor.indexOf('placeholder="Nom (optionnel)"')).toBeLessThan(editor.indexOf('placeholder="Distance km"'));
    expect(editor.indexOf('>Nom</th>')).toBeLessThan(editor.indexOf('>Distance</th>'));
    expect(editor).toContain('placeholder="Minutes ou mm:ss"');
  });

  it('places both histogram cards before collapsible splits', () => {
    const page = source('src/components/trace-planning/TracePlanningPage.tsx');
    const roadbook = source('src/components/trace-planning/RaceRoadbook.tsx');
    const distributionsIndex = page.indexOf('<PlanningCharts preview={preview} />');
    const splitsIndex = page.indexOf('id="decoupage"');

    expect(distributionsIndex).toBeGreaterThan(0);
    expect(splitsIndex).toBeGreaterThan(distributionsIndex);
    expect(page).toContain('<RaceRoadbook preview={preview} plan={plan} />');
    expect(roadbook).toContain('aria-expanded={open}');
    expect(roadbook).toContain('Splits kilométriques détaillés');
    expect(page).not.toContain('Creer le plan principal');
    expect(page).not.toContain('Créer le plan principal');
  });
});
