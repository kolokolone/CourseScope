'use client';

import * as React from 'react';

const SUB_NAV_ITEMS = [
  { id: 'apercu', label: 'Aperçu' },
  { id: 'analyse', label: 'Analyse' },
  { id: 'splits', label: 'Splits' },
  { id: 'carte', label: 'Carte' },
  { id: 'relief', label: 'Relief' },
  { id: 'zones', label: 'Zones' },
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
    <nav className="sticky top-0 z-[1001] bg-[rgba(245,247,251,0.92)] backdrop-blur-md border-b border-slate-200 mt-[14px]">
      <div className="flex gap-[6px] overflow-x-auto px-[2px] pb-[2px]">
        {SUB_NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={`relative px-[14px] py-[14px] text-sm font-semibold whitespace-nowrap transition-colors ${
              activeSection === item.id
                ? 'text-[#0f4c81]'
                : 'text-slate-600 hover:text-slate-800'
            }`}
            data-active={activeSection === item.id}
            onClick={() => onSectionClick(item.id)}
          >
            {item.label}
            {activeSection === item.id && (
              <span className="absolute left-[10px] right-[10px] bottom-0 h-[3px] rounded-t-full bg-[#1769aa]" />
            )}
          </button>
        ))}
      </div>
    </nav>
  );
}
