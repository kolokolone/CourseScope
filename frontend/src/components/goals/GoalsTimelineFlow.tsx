import * as React from 'react';

import { GoalMiniCard } from '@/components/goals/GoalMiniCard';
import type { GoalItem } from '@/types/api';

type GoalsTimelineFlowProps = {
  goals: GoalItem[];
};

const DAY_MS = 24 * 60 * 60 * 1000;

function startOfDay(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function dateAtStart(eventDate: string) {
  return startOfDay(new Date(`${eventDate}T00:00:00`));
}

function daysDeltaLabel(fromDate: Date, toDate: Date) {
  const delta = Math.round((toDate.getTime() - fromDate.getTime()) / DAY_MS);
  if (delta >= 0) return `J-${delta}`;
  return `J+${Math.abs(delta)}`;
}

function formatTodayLabel(date: Date) {
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });
}

export function GoalsTimelineFlow({ goals }: GoalsTimelineFlowProps) {
  const today = React.useMemo(() => startOfDay(new Date()), []);
  const sorted = React.useMemo(
    () => goals.slice().sort((a, b) => dateAtStart(a.event_date).getTime() - dateAtStart(b.event_date).getTime()),
    [goals]
  );

  if (sorted.length === 0) return null;

  return (
    <div className="overflow-x-auto pb-1">
      <div className="inline-flex min-w-full items-start gap-3">
        <div className="w-48 shrink-0 rounded-md border bg-card p-2 text-[11px] shadow-sm">
          <div className="font-semibold leading-tight text-foreground">Aujourd&apos;hui</div>
          <div className="text-muted-foreground">{formatTodayLabel(today)}</div>
        </div>

        {sorted.map((goal, index) => {
          const previousDate = index === 0 ? today : dateAtStart(sorted[index - 1]?.event_date ?? goal.event_date);
          const currentDate = dateAtStart(goal.event_date);
          return (
            <React.Fragment key={goal.id}>
              <div className="flex min-h-16 w-16 shrink-0 flex-col items-center justify-center gap-1" aria-hidden="true">
                <div className="rounded-full border bg-background px-2 py-0.5 text-[11px] font-medium text-foreground">{daysDeltaLabel(previousDate, currentDate)}</div>
                <div className="text-xl leading-none text-muted-foreground">→</div>
              </div>
              <GoalMiniCard goal={goal} className="w-48 shrink-0" />
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
