import * as React from 'react';

import { formatNumber } from '@/lib/metricsFormat';
import type { GoalItem } from '@/types/api';

type GoalMiniCardProps = {
  goal: GoalItem;
  className?: string;
};

function formatDateLabel(eventDate: string) {
  const date = new Date(`${eventDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return eventDate;
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function GoalMiniCard({ goal, className = '' }: GoalMiniCardProps) {
  return (
    <div className={`rounded-md border bg-card p-2 text-[11px] shadow-sm ${className}`.trim()}>
      <div className="font-semibold leading-tight text-foreground">{goal.name}</div>
      <div className="text-muted-foreground">{formatDateLabel(goal.event_date)}</div>
      <div className="text-muted-foreground">{`${formatNumber(goal.distance_km, { decimals: 1 })} km • ${goal.race_type === 'trail' ? 'Trail' : 'Course'}`}</div>
    </div>
  );
}
