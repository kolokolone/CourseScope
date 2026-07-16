import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ProgressWaterfallCard } from './ProgressWaterfallCard';


describe('ProgressWaterfallCard', () => {
  it('exposes only the native resolutions and supported activity limits', () => {
    render(
      <ProgressWaterfallCard
        activities={[]}
        isLoading={false}
        error={null}
        waterfallLimit={60}
        waterfallBinStep={10}
        onLimitChange={vi.fn()}
        onBinStepChange={vi.fn()}
      />,
    );

    const limit = screen.getByLabelText('Limit') as HTMLSelectElement;
    const binStep = screen.getByLabelText('Bin step') as HTMLSelectElement;

    expect(Array.from(limit.options, (option) => option.value)).toEqual(['10', '30', '60', '120']);
    expect(Array.from(binStep.options, (option) => option.value)).toEqual(['5', '10', '20', '30']);
    expect(limit.value).toBe('60');
    expect(binStep.value).toBe('10');
    expect(screen.queryByLabelText('Session')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Terrain')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Endurance only')).not.toBeInTheDocument();
  });
});
