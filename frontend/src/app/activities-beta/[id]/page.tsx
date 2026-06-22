'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { ActivityBetaPage } from '@/components/activity-beta/ActivityBetaPage';

export default function Page() {
  const params = useParams();
  const activityId = params.id as string;
  return <ActivityBetaPage activityId={activityId} />;
}
