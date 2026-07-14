'use client';

import { CompactAnalysisChart } from './CompactAnalysisChart';
import type { SeriesInfo } from '@/types/api';

type MainAnalysisCardProps = {
  activityId: string;
  seriesAvailable: SeriesInfo[];
  onDistanceHover?: (distanceKm: number | null) => void;
};

export function MainAnalysisCard({ activityId, seriesAvailable, onDistanceHover }: MainAnalysisCardProps) {
  if (!seriesAvailable || seriesAvailable.length === 0) return null;

  return (
    <CompactAnalysisChart
      activityId={activityId}
      seriesAvailable={seriesAvailable}
      onDistanceHover={onDistanceHover}
    />
  );
}
