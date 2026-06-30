'use client';

import { CompactAnalysisChart } from './CompactAnalysisChart';
import type { SeriesInfo } from '@/types/api';

type MainAnalysisCardProps = {
  activityId: string;
  seriesAvailable: SeriesInfo[];
};

export function MainAnalysisCard({ activityId, seriesAvailable }: MainAnalysisCardProps) {
  if (!seriesAvailable || seriesAvailable.length === 0) return null;

  return (
    <CompactAnalysisChart
      activityId={activityId}
      seriesAvailable={seriesAvailable}
    />
  );
}
