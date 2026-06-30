'use client';

import * as React from 'react';

const SUB_NAV_ITEMS = [
  { id: 'apercu', label: 'Aperçu' },
  { id: 'analyse', label: 'Analyse' },
  { id: 'carte', label: 'Carte' },
  { id: 'splits', label: 'Splits' },
  { id: 'zones', label: 'Zones' },
  { id: 'allure-pente', label: 'Allure vs Pente' },
  { id: 'relief', label: 'Relief et pente' },
  { id: 'details', label: 'Détails' },
] as const;

const SECTION_IDS = SUB_NAV_ITEMS.map((item) => item.id);

type ActivityBetaSubNavProps = {
  onSectionClick: (id: string) => void;
};

export function ActivityBetaSubNav({ onSectionClick }: ActivityBetaSubNavProps) {
  const [activeSection, setActiveSection] = React.useState(SECTION_IDS[0]);

  React.useEffect(() => {
    const observers: IntersectionObserver[] = [];

    for (const id of SECTION_IDS) {
      const el = document.getElementById(id);
      if (!el) continue;

      const observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              setActiveSection(id);
            }
          }
        },
        { rootMargin: '-100px 0px -60% 0px' }
      );
      observer.observe(el);
      observers.push(observer);
    }

    return () => observers.forEach((o) => o.disconnect());
  }, []);

  return (
    <nav className="sticky top-0 z-30 -mx-4 border-b border-slate-200 bg-slate-50/90 px-4 backdrop-blur sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
      <div className="mx-auto flex max-w-[1440px] gap-1 overflow-x-auto py-2">
        {SUB_NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={`rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap transition ${
              activeSection === item.id
                ? 'bg-blue-950 text-white shadow-sm'
                : 'text-slate-600 hover:bg-white hover:text-slate-950'
            }`}
            data-active={activeSection === item.id}
            onClick={() => onSectionClick(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
