'use client';

import * as React from 'react';
import { Target } from 'lucide-react';

import { useCreateGoal, useDeleteGoal, useGoalsList, useUpdateGoal } from '@/hooks/useGoals';
import { GoalsObjectivesMap } from '@/components/goals/GoalsObjectivesMap';
import { GoalsCalendar } from '@/components/goals/GoalsCalendar';
import { GoalsTimelineCard } from '@/components/goals/GoalsTimelineCard';
import { GoalForm } from '@/components/goals/GoalForm';
import { GoalListTable } from '@/components/goals/GoalListTable';
import {
  compareGoals,
  goalCountdownLabel,
  type SortKey,
  type SortDir,
} from '@/components/goals/utils';
import type { GoalItem } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

export default function GoalsPage() {
  const goalsQuery = useGoalsList();
  const createGoal = useCreateGoal();
  const deleteGoal = useDeleteGoal();
  const updateGoal = useUpdateGoal();

  const [isFormOpen, setIsFormOpen] = React.useState(false);
  const [editingGoalId, setEditingGoalId] = React.useState<string | null>(null);

  const [sortKey, setSortKey] = React.useState<SortKey>('date');
  const [sortDir, setSortDir] = React.useState<SortDir>('asc');

  const goals = React.useMemo(() => goalsQuery.data?.goals ?? [], [goalsQuery.data?.goals]);
  const hasGoals = goals.length > 0;
  const isSubmitting = createGoal.isPending || updateGoal.isPending;

  const editingGoal = React.useMemo(
    () => (editingGoalId ? goals.find((g) => g.id === editingGoalId) ?? null : null),
    [editingGoalId, goals]
  );

  const resetFormState = React.useCallback(() => {
    setEditingGoalId(null);
  }, []);

  const sortedGoals = React.useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1;
    return goals.slice().sort((a, b) => compareGoals(a, b, sortKey) * dir);
  }, [goals, sortDir, sortKey]);

  const today = React.useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);
  const countdownByGoalId = React.useMemo(
    () =>
      Object.fromEntries(
        goals.map((goal) => [goal.id, goalCountdownLabel(goal, today)])
      ) as Record<string, string>,
    [goals, today]
  );

  const toggleSort = (key: SortKey) => {
    setSortKey((prev) => {
      if (prev !== key) {
        setSortDir(key === 'date' ? 'asc' : 'asc');
        return key;
      }
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      return prev;
    });
  };

  const startEditingGoal = React.useCallback((goal: GoalItem) => {
    setEditingGoalId(goal.id);
    setIsFormOpen(true);
  }, []);

  const handleSubmit = React.useCallback(
    async (payload: any) => {
      if (editingGoalId) {
        const updatePayload: Record<string, unknown> = {
          name: payload.name,
          event_date: payload.event_date,
          distance_km: payload.distance_km,
          location: (payload.location as string) || null,
          location_city: (payload.location_city as string) ?? null,
          location_country: (payload.location_country as string) ?? null,
          location_country_code: (payload.location_country_code as string) ?? null,
          location_lat: (payload.location_lat as number) ?? null,
          location_lon: (payload.location_lon as number) ?? null,
          target_time_s: (payload.target_time_s as number) ?? null,
          target_pace_s_per_km: (payload.target_pace_s_per_km as number) ?? null,
          race_type: payload.race_type as 'road' | 'trail',
          notes: (payload.notes as string) || null,
        };
        await updateGoal.mutateAsync({ goalId: editingGoalId, payload: updatePayload as any });
      } else {
        await createGoal.mutateAsync(payload as any);
      }
      resetFormState();
      setIsFormOpen(false);
    },
    [editingGoalId, createGoal, updateGoal, resetFormState]
  );

  const handleClose = React.useCallback(() => {
    setIsFormOpen(false);
    resetFormState();
  }, [resetFormState]);

  const handleAdd = React.useCallback(() => {
    resetFormState();
    setIsFormOpen(true);
  }, [resetFormState]);

  return (
    <div className="space-y-4">
      {!hasGoals ? (
        <Card>
          <CardContent className="py-12">
            <div className="mx-auto flex max-w-lg flex-col items-center gap-3 text-center">
              <div className="relative h-14 w-14 text-slate-400">
                <Target className="h-14 w-14" />
                <div className="absolute left-1/2 top-1/2 h-[3px] w-14 -translate-x-1/2 -translate-y-1/2 rotate-[-35deg] rounded-full bg-slate-500/70" />
              </div>
              <div className="text-lg font-semibold">Pas d&apos;objectifs enregistre encore</div>
              <div className="text-sm text-muted-foreground">Ajoute ton premier objectif de course ou trail pour demarrer ton suivi.</div>
              <Button onClick={handleAdd}>
                Enregistrer son premier objectif
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <GoalsTimelineCard goals={goals} countdownByGoalId={countdownByGoalId} />
          <GoalForm
            isOpen={isFormOpen}
            editingGoal={editingGoal}
            isSubmitting={isSubmitting}
            onClose={handleClose}
            onSubmit={handleSubmit}
          />
          <GoalListTable
            goals={sortedGoals}
            isLoading={goalsQuery.isLoading}
            sortKey={sortKey}
            sortDir={sortDir}
            today={today}
            countdownByGoalId={countdownByGoalId}
            onSort={toggleSort}
            onEdit={startEditingGoal}
            onDelete={async (goalId) => { await deleteGoal.mutateAsync(goalId); }}
            isDeleting={deleteGoal.isPending}
            onAdd={handleAdd}
          />
          <GoalsCalendar goals={goals} />
          <Card>
            <CardContent className="px-4 pb-4">
              <GoalsObjectivesMap goals={goals} />
            </CardContent>
          </Card>
        </>
      )}

      {!hasGoals ? (
        <GoalForm
          isOpen={isFormOpen}
          editingGoal={editingGoal}
          isSubmitting={isSubmitting}
          onClose={handleClose}
          onSubmit={handleSubmit}
        />
      ) : null}
    </div>
  );
}
