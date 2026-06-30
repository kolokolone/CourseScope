import * as React from 'react';

import { GoalMiniCard } from '@/components/goals/GoalMiniCard';
import { startOfDay, dateAtStart } from '@/lib/dateUtils';
import type { GoalItem } from '@/types/api';

type GoalsTimelineFlowProps = {
  goals: GoalItem[];
  countdownByGoalId?: Record<string, string>;
};

const DAY_MS = 24 * 60 * 60 * 1000;

function daysDeltaLabel(fromDate: Date, toDate: Date) {
  const delta = Math.round((toDate.getTime() - fromDate.getTime()) / DAY_MS);
  if (delta >= 0) return `J-${delta}`;
  return `J+${Math.abs(delta)}`;
}

function connectorWidthFromDays(daysBetweenGoals: number) {
  const clamped = Math.max(1, Math.min(210, daysBetweenGoals));
  return Math.round(28 + Math.log1p(clamped) * 22);
}

function formatTodayLabel(date: Date) {
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });
}

export function GoalsTimelineFlow({ goals, countdownByGoalId }: GoalsTimelineFlowProps) {
  const today = React.useMemo(() => startOfDay(new Date()), []);
  const sorted = React.useMemo(
    () => goals.slice().sort((a, b) => dateAtStart(a.event_date).getTime() - dateAtStart(b.event_date).getTime()),
    [goals]
  );

  if (sorted.length === 0) return null;

  return (
    <div className="overflow-x-auto pb-1">
      <div className="inline-flex min-w-full items-center gap-1.5">
        <div className="min-w-[11rem] shrink-0 rounded-md border bg-card p-2 text-[11px] shadow-sm">
          <div className="font-semibold leading-tight text-foreground">Aujourd&apos;hui</div>
          <div className="text-muted-foreground">{formatTodayLabel(today)}</div>
        </div>

        {sorted.map((goal, index) => {
          const previousDate = index === 0 ? today : dateAtStart(sorted[index - 1]?.event_date ?? goal.event_date);
          const currentDate = dateAtStart(goal.event_date);
          const gapDays = Math.max(1, Math.round((currentDate.getTime() - previousDate.getTime()) / DAY_MS));
          const connectorWidth = connectorWidthFromDays(gapDays);
          const badgeLabel = countdownByGoalId?.[goal.id] ?? daysDeltaLabel(today, currentDate);
          return (
            <React.Fragment key={goal.id}>
              <div className="flex shrink-0 items-center" style={{ width: `${connectorWidth}px` }} aria-hidden="true">
                <div className="relative h-7 w-full">
                  <div className="absolute left-0 right-2 top-1/2 h-px -translate-y-1/2 bg-slate-300" />
                  <div className="absolute right-0 top-1/2 h-0 w-0 -translate-y-1/2 border-y-[4px] border-l-[7px] border-y-transparent border-l-slate-400" />
                  <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2 rounded-full border bg-background px-2 py-0.5 text-[11px] font-medium text-foreground">
                    {badgeLabel}
                  </div>
                </div>
              </div>
              <GoalMiniCard goal={goal} className="w-fit max-w-[14rem] shrink-0 self-center" />
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
