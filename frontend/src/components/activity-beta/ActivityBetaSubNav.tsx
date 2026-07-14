'use client';

import { AnalysisSubNav } from '@/components/analysis/AnalysisSubNav';

const items = [
  { id: 'apercu', label: 'Apercu' },
  { id: 'analyse', label: 'Analyse' },
  { id: 'carte', label: 'Carte' },
  { id: 'splits', label: 'Splits' },
  { id: 'zones', label: 'Zones' },
  { id: 'allure-pente', label: 'Allure vs Pente' },
  { id: 'relief', label: 'Relief et pente' },
  { id: 'details', label: 'Details' },
] as const;

export function ActivityBetaSubNav({ onSectionClick }: { onSectionClick: (id: string) => void }) {
  return <AnalysisSubNav items={items} onSectionClick={onSectionClick} />;
}
