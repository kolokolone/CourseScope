'use client';

import * as React from 'react';

export interface AnalysisNavItem { id: string; label: string }

export function resolveActiveSectionId(
  sectionTops: ReadonlyArray<{ id: string; top: number }>,
  anchorY: number,
  isAtBottom = false,
) {
  if (sectionTops.length === 0) return '';
  if (isAtBottom) return sectionTops[sectionTops.length - 1]?.id ?? '';

  let activeId = sectionTops[0]?.id ?? '';
  for (const section of sectionTops) {
    if (section.top > anchorY) break;
    activeId = section.id;
  }
  return activeId;
}

function findScrollContainer(element: HTMLElement): HTMLElement | Window {
  let parent = element.parentElement;
  while (parent) {
    const overflowY = window.getComputedStyle(parent).overflowY;
    if (overflowY === 'auto' || overflowY === 'scroll') return parent;
    parent = parent.parentElement;
  }
  return window;
}

function scrollContainerIsAtBottom(container: HTMLElement | Window) {
  if (container === window) {
    return window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;
  }
  const element = container as HTMLElement;
  return element.scrollTop + element.clientHeight >= element.scrollHeight - 2;
}

export function AnalysisSubNav({ items, onSectionClick }: { items: readonly AnalysisNavItem[]; onSectionClick?: (id: string) => void }) {
  const [active, setActive] = React.useState(items[0]?.id ?? '');
  const navRef = React.useRef<HTMLElement>(null);
  React.useEffect(() => {
    const sections = items
      .map((item) => document.getElementById(item.id))
      .filter((element): element is HTMLElement => element instanceof HTMLElement);
    if (sections.length === 0) return;

    const scrollContainer = findScrollContainer(sections[0]);
    let frame = 0;
    const update = () => {
      frame = 0;
      const anchorY = (navRef.current?.getBoundingClientRect().bottom ?? 96) + 8;
      const nextActive = resolveActiveSectionId(
        sections.map((section) => ({ id: section.id, top: section.getBoundingClientRect().top })),
        anchorY,
        scrollContainerIsAtBottom(scrollContainer),
      );
      if (nextActive) setActive((current) => current === nextActive ? current : nextActive);
    };
    const scheduleUpdate = () => {
      if (!frame) frame = window.requestAnimationFrame(update);
    };

    scrollContainer.addEventListener('scroll', scheduleUpdate, { passive: true });
    // A scroll event does not bubble. Capturing it from the document keeps the
    // navigation in sync when the application shell replaces or wraps its
    // scrolling <main> during a route transition.
    document.addEventListener('scroll', scheduleUpdate, { passive: true, capture: true });
    window.addEventListener('resize', scheduleUpdate);
    scheduleUpdate();
    return () => {
      scrollContainer.removeEventListener('scroll', scheduleUpdate);
      document.removeEventListener('scroll', scheduleUpdate, { capture: true });
      window.removeEventListener('resize', scheduleUpdate);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [items]);
  return (
    <nav ref={navRef} className="sticky top-0 z-30 -mx-4 border-b border-border bg-background/90 px-4 backdrop-blur sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
      <div className="mx-auto flex max-w-[1440px] gap-1 overflow-x-auto py-2">
        {items.map((item) => <button key={item.id} aria-current={active === item.id ? 'location' : undefined} className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${active === item.id ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`} onClick={() => { setActive(item.id); onSectionClick?.(item.id); if (!onSectionClick) document.getElementById(item.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}>{item.label}</button>)}
      </div>
    </nav>
  );
}
