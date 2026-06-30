import * as React from 'react';

import { formatNumber } from '@/lib/metricsFormat';
import { formatDateLabel } from '@/lib/dateUtils';
import type { GoalItem } from '@/types/api';

type GoalMiniCardProps = {
  goal: GoalItem;
  className?: string;
};

export function GoalMiniCard({ goal, className = '' }: GoalMiniCardProps) {
  return (
    <div className={`rounded-md border bg-card p-2 text-[11px] shadow-sm ${className}`.trim()}>
      <div className="font-semibold leading-tight text-foreground">{goal.name}</div>
      <div className="text-muted-foreground">{formatDateLabel(goal.event_date)}</div>
      <div className="text-muted-foreground">{`${formatNumber(goal.distance_km, { decimals: 1 })} km • ${goal.race_type === 'trail' ? 'Trail' : 'Course'}`}</div>
    </div>
  );
}
