'use client';

import { useParams } from 'next/navigation';

import { ActivityBetaPage } from '@/components/activity-beta/ActivityBetaPage';

export default function Page() {
  const params = useParams();
  return <ActivityBetaPage activityId={params.id as string} />;
}
