import { readFileSync } from 'fs';
import path from 'path';
import { describe, expect, it } from 'vitest';

import { MAP_METRICS, SERIES_NAMES } from './metricsRegistry';

describe('metrics registry coverage', () => {
  it('all registry series names appear in metrics_catalog', () => {
    const filePath = path.resolve(__dirname, '../../../docs/metrics_catalog.md');
    const content = readFileSync(filePath, 'utf-8');

    const missingSeries: string[] = [];
    for (const s of SERIES_NAMES) {
      if (!content.includes(s)) {
        missingSeries.push(s);
      }
    }
    expect(missingSeries).toEqual([]);
  });

  it('all registry map metrics appear in metrics_catalog', () => {
    const filePath = path.resolve(__dirname, '../../../docs/metrics_catalog.md');
    const content = readFileSync(filePath, 'utf-8');

    const missingMap: string[] = [];
    for (const m of MAP_METRICS) {
      if (!content.includes(m)) {
        missingMap.push(m);
      }
    }
    expect(missingMap).toEqual([]);
  });

  it('catalog contains key metric sections', () => {
    const filePath = path.resolve(__dirname, '../../../docs/metrics_catalog.md');
    const content = readFileSync(filePath, 'utf-8');

    const sections = [
      'Real Activity Metrics', 'Theoretical Activity Metrics',
      'Pace vs grade', 'Progression API', 'Map data',
      'Series index', 'Data Source Compatibility',
    ];
    const missingSections = sections.filter((s) => !content.includes(s));
    expect(missingSections).toEqual([]);
  });
});
