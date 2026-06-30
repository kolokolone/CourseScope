'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { GoalsTimelineFlow } from '@/components/goals/GoalsTimelineFlow';
import type { GoalItem } from '@/types/api';

type GoalsTimelineCardProps = {
  goals: GoalItem[];
  countdownByGoalId: Record<string, string>;
};

export function GoalsTimelineCard({ goals, countdownByGoalId }: GoalsTimelineCardProps) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-base">Ligne temporelle des objectifs</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <GoalsTimelineFlow goals={goals} countdownByGoalId={countdownByGoalId} />
      </CardContent>
    </Card>
  );
}
