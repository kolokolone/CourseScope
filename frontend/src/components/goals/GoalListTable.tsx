'use client';

import { Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatNumber } from '@/lib/metricsFormat';
import { goalCountdownLabel, goalObjectiveLabel, type SortKey, type SortDir } from '@/components/goals/utils';
import { formatDateLabel } from '@/lib/dateUtils';
import type { GoalItem } from '@/types/api';

type GoalListTableProps = {
  goals: GoalItem[];
  isLoading: boolean;
  sortKey: SortKey;
  sortDir: SortDir;
  today: Date;
  countdownByGoalId: Record<string, string>;
  onSort: (key: SortKey) => void;
  onEdit: (goal: GoalItem) => void;
  onDelete: (goalId: string) => Promise<void>;
  isDeleting: boolean;
  onAdd: () => void;
};

export function GoalListTable({
  goals,
  isLoading,
  sortKey,
  sortDir,
  today,
  countdownByGoalId,
  onSort,
  onEdit,
  onDelete,
  isDeleting,
  onAdd,
}: GoalListTableProps) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">Liste des objectifs</CardTitle>
          <Button size="sm" onClick={onAdd}>
            <Plus className="mr-1 h-4 w-4" />
            Ajouter un nouvel objectif
          </Button>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {isLoading ? (
          <div className="text-muted-foreground">Chargement...</div>
        ) : (
          <div className="overflow-auto rounded-md border">
            <table className="w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  {(['name', 'date', 'distance', null, 'location', 'objective', 'type', null] as const).map((key, i) => {
                    if (key === null) {
                      return key === null && i === 3 ? <th key="countdown" className="px-3 py-2 text-left font-medium">Dans :</th>
                        : <th key={`actions-${i}`} className="px-3 py-2 text-right font-medium">Actions</th>;
                    }
                    const label = key === 'name' ? 'Nom' : key === 'date' ? 'Date' : key === 'distance' ? 'Distance (km)' : key === 'location' ? 'Localisation' : key === 'objective' ? 'Objectif' : 'Type';
                    return (
                      <th key={key} className={`px-3 py-2 font-medium ${key === 'distance' ? 'text-right' : 'text-left'}`}>
                        <button type="button" className="hover:underline" onClick={() => onSort(key)}>
                          {label}
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y">
                {goals.map((goal) => (
                  <tr key={goal.id}>
                    <td className="px-3 py-2 font-medium">{goal.name}</td>
                    <td className="px-3 py-2">{formatDateLabel(goal.event_date)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{formatNumber(goal.distance_km, { decimals: 1 })}</td>
                    <td className="px-3 py-2 tabular-nums">{goalCountdownLabel(goal, today)}</td>
                    <td className="px-3 py-2">{goal.location || '—'}</td>
                    <td className="px-3 py-2 tabular-nums">{goalObjectiveLabel(goal)}</td>
                    <td className="px-3 py-2">{goal.race_type === 'trail' ? 'Trail' : 'Course à pied'}</td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="outline" onClick={() => onEdit(goal)}>
                          Modifier
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onDelete(goal.id)}
                          disabled={isDeleting}
                        >
                          Supprimer
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
