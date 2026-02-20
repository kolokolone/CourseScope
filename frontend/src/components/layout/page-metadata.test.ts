import { describe, expect, it } from 'vitest';

import { resolvePageMetadata } from './page-metadata';

describe('resolvePageMetadata', () => {
  it('returns real activity metadata for /activities/[id]', () => {
    const meta = resolvePageMetadata('/activities/abc');
    expect(meta.title).toBe('Activité');
    expect(meta.subtitle).toBe('Analyse réelle');
    expect(meta.container).toBe('wide');
  });

  it('returns trace metadata for /traces/[id]', () => {
    const meta = resolvePageMetadata('/traces/abc');
    expect(meta.title).toBe('Trace');
    expect(meta.subtitle).toBe('Analyse théorique');
    expect(meta.container).toBe('wide');
  });

  it('falls back to default metadata for unknown routes', () => {
    const meta = resolvePageMetadata('/legacy/abc/theoretical');
    expect(meta.title).toBe('CourseScope');
    expect(meta.subtitle).toBe('Analyse des activités');
    expect(meta.container).toBe('default');
  });

  it('returns static metadata for /goals', () => {
    const meta = resolvePageMetadata('/goals');
    expect(meta.title).toBe('Objectifs');
    expect(meta.subtitle).toBe('Courses et trails à venir');
    expect(meta.container).toBe('default');
  });
});
