import { readFileSync } from 'fs';
import path from 'path';
import { describe, expect, it } from 'vitest';

import { getRegistryMetricPaths, MAP_METRICS, SERIES_NAMES } from './metricsRegistry';

type MetricsListParse = {
  paths: string[];
  series: string[];
  map: string[];
};

function parseMetricsList(content: string): MetricsListParse {
  const lines = content.split(/\r?\n/);
  const paths: string[] = [];
  const series: string[] = [];
  const map: string[] = [];

  let section: 'series' | 'map' | 'other' = 'other';

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith('2.16 Series data')) {
      section = 'series';
      continue;
    }
    if (trimmed.startsWith('3) Map data')) {
      section = 'map';
      continue;
    }
    if (trimmed.startsWith('4) Theoretical')) {
      section = 'other';
      continue;
    }

    if (!trimmed.startsWith('- ')) continue;
    const entry = trimmed.slice(2);
    const bracketIndex = entry.lastIndexOf('[');
    const raw = bracketIndex > 0 ? entry.slice(0, bracketIndex).trim() : entry.trim();
    if (raw.startsWith('[Both]') || raw.startsWith('[FIT]') || raw.startsWith('[Cond]')) continue;

    const parts = raw.split(',').map((part) => part.trim()).filter(Boolean);
    if (parts.length > 1) {
      const first = parts[0];
      paths.push(first);
      const base = first.includes('records[].') ? `${first.split('records[].')[0]}records[].` : '';
      parts.slice(1).forEach((part) => {
        paths.push(base ? `${base}${part}` : part);
      });
      continue;
    }
    if (!raw) continue;

    if (section === 'series') {
      series.push(raw);
      continue;
    }
    if (section === 'map') {
      map.push(raw);
      continue;
    }

    paths.push(raw);
  }

  return { paths, series, map };
}

describe('metrics registry coverage', () => {
  it('covers all metrics_list entries', () => {
    const filePath = path.resolve(__dirname, '../../../docs/metrics_list.txt');
    const content = readFileSync(filePath, 'utf-8');
    const parsed = parseMetricsList(content);
    const registryPaths = new Set(getRegistryMetricPaths());

    const missing = parsed.paths.filter((p) => !registryPaths.has(p));
    expect(missing).toEqual([]);

    const missingSeries = parsed.series.filter((s) => !SERIES_NAMES.includes(s));
    expect(missingSeries).toEqual([]);

    const missingMap = parsed.map.filter((m) => !MAP_METRICS.includes(m));
    expect(missingMap).toEqual([]);
  });
});
