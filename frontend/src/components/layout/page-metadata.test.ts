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

  it('keeps legacy /activity/[id]/theoretical metadata', () => {
    const meta = resolvePageMetadata('/activity/abc/theoretical');
    expect(meta.title).toBe('Trace');
    expect(meta.subtitle).toBe('Analyse théorique');
    expect(meta.container).toBe('wide');
  });

  it('returns static metadata for /goals', () => {
    const meta = resolvePageMetadata('/goals');
    expect(meta.title).toBe('Objectifs');
    expect(meta.subtitle).toBe('Courses et trails à venir');
    expect(meta.container).toBe('default');
  });
});
