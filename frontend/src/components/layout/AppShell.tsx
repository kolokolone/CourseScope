'use client';

import * as React from 'react';
import { usePathname } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { metaApi } from '@/lib/api';
import { PageContainer } from './PageContainer';
import { resolvePageMetadata } from './page-metadata';
import { Sidebar } from './Sidebar';
import { TopHeader } from './TopHeader';

type AppShellProps = {
  children: React.ReactNode;
};

function formatTodayLabel() {
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'medium',
  }).format(new Date());
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname() ?? '/';
  const [mobileSidebarOpen, setMobileSidebarOpen] = React.useState(false);

  const pageMetadata = React.useMemo(() => resolvePageMetadata(pathname), [pathname]);
  const HeaderActions = pageMetadata.HeaderActions;
  const contextInfo = pageMetadata.showToday ? formatTodayLabel() : undefined;

  const versionQuery = useQuery({
    queryKey: ['meta', 'root'],
    queryFn: () => metaApi.root(),
    staleTime: 60_000,
  });

  React.useEffect(() => {
    setMobileSidebarOpen(false);
  }, [pathname]);

  React.useEffect(() => {
    if (!mobileSidebarOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMobileSidebarOpen(false);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [mobileSidebarOpen]);

  return (
    <div className="h-screen overflow-hidden bg-background text-foreground">
      <div className="grid h-full md:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="hidden h-screen overflow-y-auto border-r border-border md:block">
          <Sidebar pathname={pathname} version={versionQuery.data?.version} />
        </aside>

        <div className="flex min-h-0 flex-col">
          <TopHeader
            title={pageMetadata.title}
            subtitle={pageMetadata.subtitle}
            onOpenSidebar={() => setMobileSidebarOpen(true)}
            contextInfo={contextInfo}
            actions={HeaderActions ? <HeaderActions /> : null}
          />

          <main className="min-h-0 flex-1 overflow-y-auto">
            <PageContainer variant={pageMetadata.container}>{children}</PageContainer>
          </main>
        </div>
      </div>

      {mobileSidebarOpen ? (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true">
          <button
            type="button"
            className="absolute inset-0 bg-black/45"
            onClick={() => setMobileSidebarOpen(false)}
            aria-label="Fermer la navigation"
          />
          <div className="relative h-full w-[18rem] max-w-[88vw] border-r border-border bg-card">
            <Sidebar pathname={pathname} onNavigate={() => setMobileSidebarOpen(false)} version={versionQuery.data?.version} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
