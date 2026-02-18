import type { ComponentType } from 'react';
import { ActivitiesHeaderActions } from './HeaderActions';
import type { ContainerVariant } from './PageContainer';

type PageMetadata = {
  title: string;
  subtitle?: string;
  container: ContainerVariant;
  HeaderActions?: ComponentType;
  showToday?: boolean;
};

const STATIC_PAGE_METADATA: Record<string, PageMetadata> = {
  '/': {
    title: 'Page d’accueil',
    subtitle: 'Upload et exploration des activités',
    container: 'default',
  },
  '/activities': {
    title: 'Activités',
    subtitle: 'Historique, tri et synchronisation',
    container: 'default',
    HeaderActions: ActivitiesHeaderActions,
  },
  '/progress': {
    title: 'Progression',
    subtitle: 'Tendances multi-activités',
    container: 'default',
    showToday: true,
  },
  '/settings': {
    title: 'Paramètres',
    subtitle: 'Configuration de l’application',
    container: 'default',
  },
};

const FALLBACK_PAGE_METADATA: PageMetadata = {
  title: 'CourseScope',
  subtitle: 'Analyse des activités',
  container: 'default',
};

function normalizePathname(pathname: string) {
  if (pathname.length > 1 && pathname.endsWith('/')) {
    return pathname.slice(0, -1);
  }
  return pathname;
}

function isDynamicActivityRoute(pathname: string) {
  return /^\/activity\/[^/]+\/(real|theoretical)$/.test(pathname);
}

export function resolvePageMetadata(pathname: string): PageMetadata {
  const normalizedPathname = normalizePathname(pathname);

  if (isDynamicActivityRoute(normalizedPathname)) {
    const subtitle = normalizedPathname.endsWith('/real') ? 'Analyse réelle' : 'Analyse théorique';
    return {
      title: 'Activité',
      subtitle,
      container: 'wide',
    };
  }

  return STATIC_PAGE_METADATA[normalizedPathname] ?? FALLBACK_PAGE_METADATA;
}
