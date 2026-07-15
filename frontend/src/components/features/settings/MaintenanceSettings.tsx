'use client';

import * as React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { progressApi } from '@/lib/api';
import type { ProgressIndexStatusResponse } from '@/types/api';
import { Settings, Trash2 } from 'lucide-react';
import { useCleanupActivities } from '@/hooks/useActivity';
import { useCleanupGoals } from '@/hooks/useGoals';
import { useCleanupTraces } from '@/hooks/useTraces';

function formatIndexationMode(mode: ProgressIndexStatusResponse['mode']): string {
  if (mode === 'fast') return 'rapide';
  if (mode === 'slow') return 'complete';
  return 'inconnue';
}

export function MaintenanceSettings() {
  const queryClient = useQueryClient();

  const cleanupMutation = useCleanupActivities();
  const cleanupTracesMutation = useCleanupTraces();
  const cleanupGoalsMutation = useCleanupGoals();

  const progressIndexStatus = useQuery<ProgressIndexStatusResponse>({
    queryKey: ['progress', 'index-status'],
    queryFn: () => progressApi.indexStatus(),
    staleTime: 2_000,
    refetchInterval: (query) => {
      const state = query.state.data as ProgressIndexStatusResponse | undefined;
      return state?.running ? 2_000 : 5_000;
    },
  });

  const indexFastMutation = useMutation<ProgressIndexStatusResponse, Error, void>({
    mutationFn: () => progressApi.indexFast({ reason: 'settings_manual_fast' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['progress', 'index-status'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
    },
  });

  const indexFullMutation = useMutation<ProgressIndexStatusResponse, Error, void>({
    mutationFn: () =>
      progressApi.indexSlow({
        strategy: 'backfill_full',
        reason: 'settings_manual',
        force: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['progress', 'index-status'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
    },
  });

  const handleCleanup = async () => {
    if (window.confirm('Supprimer toutes les activites sur disque ?')) {
      try {
        await cleanupMutation.mutateAsync();
        queryClient.invalidateQueries({ queryKey: ['activities'] });
      } catch {
        alert('Echec du nettoyage des activites');
      }
    }
  };

  const handleCleanupTraces = async () => {
    if (window.confirm('Supprimer toutes les traces GPX enregistrees ?')) {
      try {
        await cleanupTracesMutation.mutateAsync();
        queryClient.invalidateQueries({ queryKey: ['traces'] });
      } catch {
        alert('Echec du nettoyage des traces');
      }
    }
  };

  const handleCleanupGoals = async () => {
    if (window.confirm('Supprimer tous les objectifs enregistres ?')) {
      try {
        await cleanupGoalsMutation.mutateAsync();
        queryClient.invalidateQueries({ queryKey: ['goals'] });
      } catch {
        alert('Echec du nettoyage des objectifs');
      }
    }
  };

  const handleFastIndexation = async () => {
    try {
      await indexFastMutation.mutateAsync();
      await progressIndexStatus.refetch();
    } catch {
      alert('Echec du lancement de l indexation rapide');
    }
  };

  const handleFullIndexation = async () => {
    if (!window.confirm('Lancer une indexation complete (recalcul total) ?')) return;
    try {
      await indexFullMutation.mutateAsync();
      await progressIndexStatus.refetch();
    } catch {
      alert('Echec du lancement de l indexation complete');
    }
  };

  const isIndexationRunning = progressIndexStatus.data?.running === true;
  const indexationModeLabel = formatIndexationMode(progressIndexStatus.data?.mode ?? null);
  const indexationPercent =
    typeof progressIndexStatus.data?.percent === 'number'
      ? Math.max(0, Math.min(100, progressIndexStatus.data.percent))
      : 0;

  return (
    <Card className="rounded-2xl border border-[var(--hairline)] bg-[var(--surface-card)]">
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-base flex items-center gap-2">
          <Settings className="h-4 w-4" />
          Maintenance
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={handleCleanup} disabled={cleanupMutation.isPending}>
            <Trash2 className="h-4 w-4 mr-2" />
            Nettoyer activites
          </Button>

          <Button size="sm" variant="outline" onClick={handleCleanupTraces} disabled={cleanupTracesMutation.isPending}>
            <Trash2 className="h-4 w-4 mr-2" />
            Nettoyer traces GPX
          </Button>

          <Button size="sm" variant="outline" onClick={handleCleanupGoals} disabled={cleanupGoalsMutation.isPending}>
            <Trash2 className="h-4 w-4 mr-2" />
            Nettoyer objectifs
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleFastIndexation}
            disabled={indexFastMutation.isPending || indexFullMutation.isPending || isIndexationRunning}
          >
            <Settings className="h-4 w-4 mr-2" />
            Indexation rapide
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleFullIndexation}
            disabled={indexFastMutation.isPending || indexFullMutation.isPending || isIndexationRunning}
          >
            <Settings className="h-4 w-4 mr-2" />
            Indexation complete
          </Button>
        </div>

        <div className="mt-3 text-sm text-muted-foreground">
          {progressIndexStatus.isLoading ? (
            <span>Etat indexation: chargement...</span>
          ) : progressIndexStatus.isError ? (
            <span>Etat indexation: indisponible</span>
          ) : progressIndexStatus.data ? (
            <span>
              Etat indexation: {progressIndexStatus.data.running ? `indexation ${indexationModeLabel} en cours` : 'au repos'}
              {progressIndexStatus.data.last_result
                ? ` • scan=${progressIndexStatus.data.last_result.scanned}, ajoutees=${progressIndexStatus.data.last_result.added}, supprimees=${progressIndexStatus.data.last_result.deleted}, indexees=${progressIndexStatus.data.last_result.indexed}, a_jour=${progressIndexStatus.data.last_result.up_to_date}, erreurs=${progressIndexStatus.data.last_result.errors}`
                : ''}
              {progressIndexStatus.data.last_error ? ` • erreur: ${progressIndexStatus.data.last_error}` : ''}
            </span>
          ) : (
            <span>Etat indexation: inconnu</span>
          )}
        </div>

        {progressIndexStatus.data ? (
          <div className="mt-2">
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${indexationPercent}%` }} />
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              Progression: {progressIndexStatus.data.progress_current}/{progressIndexStatus.data.progress_total} ({indexationPercent.toFixed(1)}%)
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
