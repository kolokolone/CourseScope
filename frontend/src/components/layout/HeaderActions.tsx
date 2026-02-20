'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { garminApi, metaApi } from '@/lib/api';

export function ActivitiesHeaderActions() {
  const queryClient = useQueryClient();

  const syncMutation = useMutation({
    mutationFn: () => garminApi.sync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'] });
    },
  });

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => syncMutation.mutate()}
      disabled={syncMutation.isPending}
      title="Synchroniser avec Garmin"
    >
      <RefreshCw className="mr-2 h-4 w-4" />
      Sync Garmin
    </Button>
  );
}

export function SettingsHeaderVersion() {
  const versionQuery = useQuery({
    queryKey: ['meta', 'root'],
    queryFn: () => metaApi.root(),
    staleTime: 60_000,
  });

  const version = versionQuery.data?.version;
  return <div className="text-sm text-muted-foreground tabular-nums">{version ? `v${version}` : 'v...'}</div>;
}
