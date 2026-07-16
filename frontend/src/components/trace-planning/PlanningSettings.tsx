'use client';

import * as React from 'react';
import { Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  useActivateScenario,
  useCreateScenario,
  useUpdatePlan,
  useUpdateScenario,
} from '@/hooks/useTraces';
import {
  defaultRaceTarget,
  formatRaceTarget,
  parseRaceTarget,
} from '@/lib/raceTargetFormat';
import type {
  RaceObjectiveType,
  RacePlan,
  RaceScenario,
  TraceId,
} from '@/types/api';

function isValidIsoDate(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year
    && parsed.getUTCMonth() === month - 1
    && parsed.getUTCDate() === day;
}

export function PlanningSettings({
  traceId,
  plan,
  scenario,
}: {
  traceId: TraceId;
  plan: RacePlan;
  scenario: RaceScenario;
}) {
  const updatePlan = useUpdatePlan(traceId, plan.id);
  const updateScenario = useUpdateScenario(traceId, plan.id, scenario.id);
  const activateScenario = useActivateScenario(traceId, plan.id);
  const createScenario = useCreateScenario(traceId, plan.id);

  const [objectiveType, setObjectiveType] = React.useState<RaceObjectiveType>(scenario.objective_type);
  const [target, setTarget] = React.useState(() => formatRaceTarget(scenario.objective_type, scenario.target_value));
  const [targetError, setTargetError] = React.useState<string | null>(null);
  const [raceDate, setRaceDate] = React.useState(plan.race_date ?? '');
  const [startTime, setStartTime] = React.useState(plan.start_time ?? '');

  React.useEffect(() => {
    setObjectiveType(scenario.objective_type);
    setTarget(formatRaceTarget(scenario.objective_type, scenario.target_value));
    setTargetError(null);
  }, [scenario.id, scenario.objective_type, scenario.target_value]);

  React.useEffect(() => {
    setRaceDate(plan.race_date ?? '');
    setStartTime(plan.start_time ?? '');
  }, [plan.id]); // eslint-disable-line react-hooks/exhaustive-deps -- preserve an in-progress native date edit across refetches

  const changeObjective = (next: RaceObjectiveType) => {
    setObjectiveType(next);
    setTarget(next === scenario.objective_type
      ? formatRaceTarget(next, scenario.target_value)
      : defaultRaceTarget(next));
    setTargetError(null);
  };

  const saveObjective = () => {
    const parsed = parseRaceTarget(objectiveType, target);
    if (parsed === null || parsed <= 0) {
      setTargetError(objectiveType === 'pace'
        ? 'Saisissez une allure au format min:ss, par exemple 5:30.'
        : objectiveType === 'time'
          ? 'Saisissez un temps au format hh:mm:ss, par exemple 03:45:00.'
          : 'Saisissez un pourcentage de VMA.');
      return;
    }
    if (objectiveType === 'pace' && (parsed < 120 || parsed > 1800)) {
      setTargetError("L'allure doit être comprise entre 2:00 et 30:00 min/km.");
      return;
    }
    if (objectiveType === 'effort' && (parsed < 0.3 || parsed > 1.05)) {
      setTargetError("L'effort doit être compris entre 30 et 105 % de VMA.");
      return;
    }
    setTargetError(null);
    updateScenario.mutate({ objective_type: objectiveType, target_value: parsed });
  };

  const handleDateChange = (next: string) => {
    setRaceDate(next);
    if (isValidIsoDate(next)) updatePlan.mutate({ race_date: next });
  };

  const handleDateBlur = () => {
    if (!raceDate) updatePlan.mutate({ race_date: null });
  };

  const handleStartTimeChange = (next: string) => {
    setStartTime(next);
    if (/^([01]\d|2[0-3]):[0-5]\d$/.test(next)) {
      updatePlan.mutate({ start_time: next });
    }
  };

  const handleStartTimeBlur = () => {
    if (!startTime) updatePlan.mutate({ start_time: null });
  };

  const addScenario = async () => {
    const name = window.prompt('Nom du scénario', `Scénario ${plan.scenarios.length + 1}`)?.trim();
    if (!name) return;
    await createScenario.mutateAsync({
      name,
      objective_type: scenario.objective_type,
      target_value: scenario.target_value,
      slope_model: 'minetti',
      is_active: true,
    });
  };

  const targetPlaceholder = objectiveType === 'pace'
    ? '5:30'
    : objectiveType === 'time'
      ? '03:45:00'
      : '75';
  const targetUnit = objectiveType === 'pace'
    ? 'min/km'
    : objectiveType === 'time'
      ? 'hh:mm:ss'
      : '% VMA';

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <div className="space-y-3 lg:col-span-7">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <label className="text-sm">
            <span className="mb-1 block text-muted-foreground">Scénario actif</span>
            <select
              className="h-10 w-full rounded-md border bg-background px-3"
              value={scenario.id}
              onChange={(event) => activateScenario.mutate(event.target.value as RaceScenario['id'])}
              disabled={activateScenario.isPending}
            >
              {plan.scenarios.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-muted-foreground">Objectif</span>
            <select
              className="h-10 w-full rounded-md border bg-background px-3"
              value={objectiveType}
              onChange={(event) => changeObjective(event.target.value as RaceObjectiveType)}
            >
              <option value="pace">Allure cible</option>
              <option value="time">Temps total</option>
              <option value="effort">Effort cible</option>
            </select>
          </label>
          <div className="text-sm">
            <label htmlFor="race-target" className="mb-1 block text-muted-foreground">Valeur cible</label>
            <div className="flex flex-col gap-2 md:flex-row">
              <div className="relative min-w-0 flex-1">
                <input
                  id="race-target"
                  className="h-10 w-full rounded-md border bg-background px-3 pr-20 font-mono"
                  type="text"
                  inputMode={objectiveType === 'effort' ? 'decimal' : 'numeric'}
                  placeholder={targetPlaceholder}
                  value={target}
                  aria-invalid={Boolean(targetError)}
                  onChange={(event) => setTarget(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') saveObjective();
                  }}
                />
                <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-muted-foreground">
                  {targetUnit}
                </span>
              </div>
              <Button className="w-full md:w-auto" onClick={saveObjective} disabled={updateScenario.isPending}>Appliquer</Button>
            </div>
          </div>
        </div>
        {targetError ? <p className="text-xs text-destructive">{targetError}</p> : null}
        <p className="text-xs text-muted-foreground">
          L’allure cible est la référence sur terrain plat. Le backend conserve les secondes comme unité canonique et résout numériquement les objectifs de temps. Modèle de pente : Minetti.
        </p>
      </div>

      <div className="space-y-3 lg:col-span-5">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <label className="text-sm">
            <span className="mb-1 block text-muted-foreground">Date</span>
            <input
              className="h-10 w-full rounded-md border bg-background px-3"
              type="date"
              min="1900-01-01"
              max="2200-12-31"
              value={raceDate}
              onChange={(event) => handleDateChange(event.target.value)}
              onBlur={handleDateBlur}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-muted-foreground">Départ</span>
            <input
              className="h-10 w-full rounded-md border bg-background px-3"
              type="time"
              step={60}
              value={startTime}
              onChange={(event) => handleStartTimeChange(event.target.value)}
              onBlur={handleStartTimeBlur}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-muted-foreground">Fuseau</span>
            <input
              className="h-10 w-full rounded-md border bg-muted px-3 text-muted-foreground"
              value={plan.timezone}
              readOnly
            />
          </label>
        </div>
        <Button className="w-full md:w-auto" variant="outline" size="sm" onClick={addScenario}>
          <Plus className="mr-1 h-4 w-4" />Nouveau scénario
        </Button>
      </div>
    </div>
  );
}
