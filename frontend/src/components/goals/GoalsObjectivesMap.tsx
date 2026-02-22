'use client';

import dynamic from 'next/dynamic';

import type { GoalItem } from '@/types/api';

const GoalsObjectivesMapLeaflet = dynamic(
  () => import('@/components/goals/GoalsObjectivesMapLeaflet').then((m) => m.GoalsObjectivesMapLeaflet),
  {
    ssr: false,
    loading: () => <div className="rounded-lg border bg-gray-100" style={{ height: '420px' }} />,
  }
);

export function GoalsObjectivesMap({ goals }: { goals: GoalItem[] }) {
  return <GoalsObjectivesMapLeaflet goals={goals} />;
}
