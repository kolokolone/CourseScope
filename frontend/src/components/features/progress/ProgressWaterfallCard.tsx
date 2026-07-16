'use client';

import * as React from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PaceHr3DChart } from '@/components/charts/PaceHr3DChart';
import type { ProgressPaceHrWaterfallActivity } from '@/types/api';

type ProgressWaterfallCardProps = {
  activities: ProgressPaceHrWaterfallActivity[];
  isLoading: boolean;
  error: Error | null;
  waterfallLimit: 10 | 30 | 60 | 120;
  waterfallBinStep: 5 | 10 | 20 | 30;
  onLimitChange: (limit: 10 | 30 | 60 | 120) => void;
  onBinStepChange: (step: 5 | 10 | 20 | 30) => void;
};

export function ProgressWaterfallCard({
  activities,
  isLoading,
  error,
  waterfallLimit,
  waterfallBinStep,
  onLimitChange,
  onBinStepChange,
}: ProgressWaterfallCardProps) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <div className="flex flex-col items-stretch gap-3 md:flex-row md:items-center md:justify-between">
          <CardTitle className="text-base">Pace-HR Waterfall 3D</CardTitle>
          <div className="grid grid-cols-1 gap-2 text-sm text-muted-foreground md:flex md:flex-wrap md:items-center md:gap-3">
            <label className="flex flex-col gap-1 md:flex-row md:items-center md:gap-2">
              Limit
              <select
                className="h-9 w-full rounded-md border bg-background px-2 text-sm md:h-8 md:w-auto"
                value={waterfallLimit}
                onChange={(e) => onLimitChange(Number(e.target.value) as 10 | 30 | 60 | 120)}
              >
                <option value={10}>10</option>
                <option value={30}>30</option>
                <option value={60}>60</option>
                <option value={120}>120</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 md:flex-row md:items-center md:gap-2">
              Bin step
              <select
                className="h-9 w-full rounded-md border bg-background px-2 text-sm md:h-8 md:w-auto"
                value={waterfallBinStep}
                onChange={(e) => onBinStepChange(Number(e.target.value) as 5 | 10 | 20 | 30)}
              >
                <option value={5}>5 s/km</option>
                <option value={10}>10 s/km</option>
                <option value={20}>20 s/km</option>
                <option value={30}>30 s/km</option>
              </select>
            </label>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {isLoading ? (
          <div className="text-muted-foreground">Chargement...</div>
        ) : error ? (
          <div className="text-sm text-red-600">Erreur de chargement.</div>
        ) : (activities?.length ?? 0) === 0 ? (
          <div className="text-muted-foreground">Pas assez de donnees pour afficher le waterfall 3D.</div>
        ) : (
          <>
            <PaceHr3DChart activities={activities} />
            <div className="mt-2 text-xs text-muted-foreground">
              Les courbes sont ordonnees de l ancien au recent (gris vers rouge). A allure equivalente, une FC plus basse indique une progression.
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
