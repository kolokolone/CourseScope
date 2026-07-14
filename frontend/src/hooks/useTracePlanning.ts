'use client';

import * as React from 'react';

import { useCreatePlan, usePlanPreview, useRacePlan, useTraceDetail } from '@/hooks/useTraces';
import type { RacePlanId, RaceScenarioId, TraceId } from '@/types/api';

export function useTracePlanning(traceId: TraceId) {
  const detail = useTraceDetail(traceId);
  const activePlanId = detail.data?.active_plan?.id ?? detail.data?.plans[0]?.id ?? null;
  const plan = useRacePlan(traceId, activePlanId);
  const [selectedScenarioId, setSelectedScenarioId] = React.useState<RaceScenarioId | null>(null);

  React.useEffect(() => {
    if (!plan.data) return;
    const activeId = plan.data.active_scenario_id ?? plan.data.scenarios[0]?.id ?? null;
    if (activeId && activeId !== selectedScenarioId) setSelectedScenarioId(activeId);
  }, [plan.data, selectedScenarioId]);

  const previewPayload = activePlanId && selectedScenarioId ? { plan_id: activePlanId, scenario_id: selectedScenarioId } : null;
  const preview = usePlanPreview(traceId, previewPayload);
  const createPlan = useCreatePlan(traceId);
  const selectedScenario = plan.data?.scenarios.find((scenario) => scenario.id === selectedScenarioId) ?? null;

  return {
    detail,
    plan,
    preview,
    createPlan,
    activePlanId: activePlanId as RacePlanId | null,
    selectedScenario,
    selectedScenarioId,
    setSelectedScenarioId,
  };
}
