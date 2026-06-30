'use client';

import * as React from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PaceHr3DChart } from '@/components/charts/PaceHr3DChart';
import type { ProgressPaceHrWaterfallActivity, ProgressSessionTag, ProgressTerrainTag } from '@/types/api';
import { SESSION_FILTER_OPTIONS, TERRAIN_FILTER_OPTIONS } from '@/components/features/progress/constants';

type ProgressWaterfallCardProps = {
  activities: ProgressPaceHrWaterfallActivity[];
  isLoading: boolean;
  error: Error | null;
  waterfallLimit: 10 | 30 | 60;
  waterfallBinStep: 5 | 10;
  waterfallSessionTag: 'all' | ProgressSessionTag;
  waterfallTerrainTag: 'all' | ProgressTerrainTag;
  waterfallEnduranceOnly: boolean;
  onLimitChange: (limit: 10 | 30 | 60) => void;
  onBinStepChange: (step: 5 | 10) => void;
  onSessionTagChange: (tag: 'all' | ProgressSessionTag) => void;
  onTerrainTagChange: (tag: 'all' | ProgressTerrainTag) => void;
  onEnduranceOnlyChange: (value: boolean) => void;
};

export function ProgressWaterfallCard({
  activities,
  isLoading,
  error,
  waterfallLimit,
  waterfallBinStep,
  waterfallSessionTag,
  waterfallTerrainTag,
  waterfallEnduranceOnly,
  onLimitChange,
  onBinStepChange,
  onSessionTagChange,
  onTerrainTagChange,
  onEnduranceOnlyChange,
}: ProgressWaterfallCardProps) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="text-base">Pace-HR Waterfall 3D</CardTitle>
          <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            <label className="flex items-center gap-2">
              Limit
              <select
                className="h-8 rounded-md border bg-background px-2 text-sm"
                value={waterfallLimit}
                onChange={(e) => onLimitChange(Number(e.target.value) as 10 | 30 | 60)}
              >
                <option value={10}>10</option>
                <option value={30}>30</option>
                <option value={60}>60</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              Bin step
              <select
                className="h-8 rounded-md border bg-background px-2 text-sm"
                value={waterfallBinStep}
                onChange={(e) => onBinStepChange(Number(e.target.value) as 5 | 10)}
              >
                <option value={5}>5s</option>
                <option value={10}>10s</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              Session
              <select
                className="h-8 rounded-md border bg-background px-2 text-sm"
                value={waterfallSessionTag}
                onChange={(e) => onSessionTagChange(e.target.value as 'all' | ProgressSessionTag)}
              >
                {SESSION_FILTER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2">
              Terrain
              <select
                className="h-8 rounded-md border bg-background px-2 text-sm"
                value={waterfallTerrainTag}
                onChange={(e) => onTerrainTagChange(e.target.value as 'all' | ProgressTerrainTag)}
              >
                {TERRAIN_FILTER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={waterfallEnduranceOnly}
                onChange={(e) => onEnduranceOnlyChange(e.target.checked)}
              />
              Endurance only
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
          <div className="text-muted-foreground">Pas assez de donnees pour afficher le waterfall 3D avec les filtres actuels.</div>
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
