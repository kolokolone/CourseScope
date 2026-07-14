'use client';

import { useParams } from 'next/navigation';

import { TracePlanningPage } from '@/components/trace-planning/TracePlanningPage';
import { asTraceId } from '@/types/api';

export default function TracePage() {
  const params = useParams<{ id: string }>();
  return <TracePlanningPage traceId={asTraceId(params.id)} />;
}
