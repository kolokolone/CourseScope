import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { RacePlan, RacePlanId, RaceScenario, RaceScenarioId, TraceId } from '@/types/api';
import { PlanningSettings } from './PlanningSettings';

const hooks = vi.hoisted(() => ({
  updatePlan: vi.fn(),
  updateScenario: vi.fn(),
  activateScenario: vi.fn(),
  createScenario: vi.fn(),
}));

vi.mock('@/hooks/useTraces', () => ({
  useUpdatePlan: () => ({ mutate: hooks.updatePlan, isPending: false }),
  useUpdateScenario: () => ({ mutate: hooks.updateScenario, isPending: false }),
  useActivateScenario: () => ({ mutate: hooks.activateScenario, isPending: false }),
  useCreateScenario: () => ({ mutateAsync: hooks.createScenario, isPending: false }),
}));

const traceId = 'trace-1' as TraceId;
const planId = 'plan-1' as RacePlanId;
const scenarioId = 'scenario-1' as RaceScenarioId;
const scenario: RaceScenario = {
  id: scenarioId,
  race_plan_id: planId,
  name: 'Principal',
  objective_type: 'pace',
  target_value: 300,
  slope_model: 'minetti',
  calibration_factor: 1,
  is_active: true,
  stops: [],
};
const plan: RacePlan = {
  id: planId,
  trace_id: traceId,
  name: 'Plan principal',
  race_date: null,
  start_time: '08:00',
  timezone: 'Europe/Paris',
  active_scenario_id: scenarioId,
  scenarios: [scenario],
};

describe('PlanningSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows and persists a pace target as min:ss instead of raw seconds', () => {
    render(<PlanningSettings traceId={traceId} plan={plan} scenario={scenario} />);

    expect(screen.getByLabelText('Valeur cible')).toHaveValue('5:00');
    fireEvent.change(screen.getByLabelText('Valeur cible'), { target: { value: '5:30' } });
    fireEvent.click(screen.getByRole('button', { name: 'Appliquer' }));

    expect(hooks.updateScenario).toHaveBeenCalledWith({ objective_type: 'pace', target_value: 330 });
  });

  it('keeps the selected date stable across a stale plan refetch', () => {
    const view = render(<PlanningSettings traceId={traceId} plan={plan} scenario={scenario} />);
    const dateInput = screen.getByLabelText('Date');

    fireEvent.change(dateInput, { target: { value: '2026-07-14' } });
    expect(hooks.updatePlan).toHaveBeenCalledWith({ race_date: '2026-07-14' });

    view.rerender(<PlanningSettings traceId={traceId} plan={{ ...plan, race_date: null }} scenario={scenario} />);
    expect(screen.getByLabelText('Date')).toHaveValue('2026-07-14');
  });
});
