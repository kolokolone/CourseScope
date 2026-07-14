'use client';

import * as React from 'react';

export interface AnalysisNavItem { id: string; label: string }

export function AnalysisSubNav({ items, onSectionClick }: { items: readonly AnalysisNavItem[]; onSectionClick?: (id: string) => void }) {
  const [active, setActive] = React.useState(items[0]?.id ?? '');
  React.useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (visible?.target.id) setActive(visible.target.id);
    }, { rootMargin: '-96px 0px -65% 0px', threshold: [0, 0.1] });
    items.forEach((item) => { const element = document.getElementById(item.id); if (element) observer.observe(element); });
    return () => observer.disconnect();
  }, [items]);
  return (
    <nav className="sticky top-0 z-30 -mx-4 border-b border-border bg-background/90 px-4 backdrop-blur sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
      <div className="mx-auto flex max-w-[1440px] gap-1 overflow-x-auto py-2">
        {items.map((item) => <button key={item.id} className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${active === item.id ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`} onClick={() => { onSectionClick?.(item.id); if (!onSectionClick) document.getElementById(item.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}>{item.label}</button>)}
      </div>
    </nav>
  );
}
