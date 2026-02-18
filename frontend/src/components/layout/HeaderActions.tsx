'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { garminApi } from '@/lib/api';

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
