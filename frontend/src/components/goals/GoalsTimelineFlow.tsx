import * as React from 'react';
import { CalendarDays, Flag, MapPin, Route } from 'lucide-react';

import { goalObjectiveLabel } from '@/components/goals/utils';
import { startOfDay, dateAtStart, formatDateLabel } from '@/lib/dateUtils';
import { formatNumber } from '@/lib/metricsFormat';
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

export function connectorWidthFromDays(daysBetweenGoals: number) {
  const clamped = Math.max(1, Math.min(210, daysBetweenGoals));
  return Math.round(36 + Math.log1p(clamped) * 16);
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
    <div className="overflow-x-auto pb-2">
      <div className="relative inline-flex min-w-full items-start pt-1">
        <div className="absolute left-24 right-28 top-5 h-px bg-border" aria-hidden="true" />

        <div className="relative w-48 shrink-0">
          <div className="flex h-10 items-center justify-center">
            <span className="relative z-10 h-3 w-3 rounded-full border-2 border-primary bg-card shadow-sm" />
          </div>
          <div className="rounded-xl border border-border bg-muted/35 p-3 text-sm">
            <div className="font-semibold text-foreground">Aujourd&apos;hui</div>
            <div className="mt-1 text-xs text-muted-foreground">{formatTodayLabel(today)}</div>
          </div>
        </div>

        {sorted.map((goal, index) => {
          const previousDate = index === 0 ? today : dateAtStart(sorted[index - 1]?.event_date ?? goal.event_date);
          const currentDate = dateAtStart(goal.event_date);
          const gapDays = Math.max(1, Math.round((currentDate.getTime() - previousDate.getTime()) / DAY_MS));
          const connectorWidth = connectorWidthFromDays(gapDays);
          const badgeLabel = countdownByGoalId?.[goal.id] ?? daysDeltaLabel(today, currentDate);
          const location = goal.location_city || goal.location;

          return (
            <React.Fragment key={goal.id}>
              <div className="relative h-10 shrink-0" style={{ width: `${connectorWidth}px` }} aria-label={`${gapDays} jours`}>
                <span className="absolute left-1/2 top-5 z-10 -translate-x-1/2 -translate-y-1/2 whitespace-nowrap rounded-full border border-border bg-card px-2 py-0.5 text-[11px] font-semibold text-primary shadow-sm">
                  {badgeLabel}
                </span>
              </div>

              <article className="relative w-60 shrink-0">
                <div className="flex h-10 items-center justify-center">
                  <span className="relative z-10 grid h-6 w-6 place-items-center rounded-full border border-primary/30 bg-card text-primary shadow-sm">
                    <Flag className="h-3.5 w-3.5" />
                  </span>
                </div>
                <div className={`rounded-xl border p-3 shadow-sm ${index === 0 ? 'border-primary/40 bg-primary/[0.035]' : 'border-border bg-card'}`}>
                  <div className="truncate font-semibold text-foreground" title={goal.name}>{goal.name}</div>
                  <div className="mt-2 space-y-1.5 text-xs text-muted-foreground">
                    <div className="flex items-center gap-1.5"><CalendarDays className="h-3.5 w-3.5" />{formatDateLabel(goal.event_date)}</div>
                    <div className="flex items-center gap-1.5"><Route className="h-3.5 w-3.5" />{formatNumber(goal.distance_km, { decimals: 1 })} km · {goalObjectiveLabel(goal)}</div>
                    {location ? <div className="flex items-center gap-1.5 truncate"><MapPin className="h-3.5 w-3.5 shrink-0" /><span className="truncate">{location}</span></div> : null}
                  </div>
                </div>
              </article>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
