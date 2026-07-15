import { describe, expect, it } from 'vitest';

import { resolveActiveSectionId } from './AnalysisSubNav';

describe('resolveActiveSectionId', () => {
  const sections = [
    { id: 'parametres', top: -400 },
    { id: 'apercu', top: -20 },
    { id: 'carte', top: 180 },
    { id: 'splits', top: 900 },
  ];

  it('follows document order instead of observer callback order', () => {
    expect(resolveActiveSectionId(sections, 120)).toBe('apercu');
  });

  it('selects the final section at the bottom of the scroll container', () => {
    expect(resolveActiveSectionId(sections, 120, true)).toBe('splits');
  });
});
