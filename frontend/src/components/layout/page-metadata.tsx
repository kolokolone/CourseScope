import type { ComponentType } from 'react';
import { ActivitiesHeaderActions, SettingsHeaderVersion } from './HeaderActions';
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
    showToday: true,
  },
  '/activities': {
    title: 'Activités',
    subtitle: 'Historique, tri et synchronisation',
    container: 'default',
    HeaderActions: ActivitiesHeaderActions,
    showToday: true,
  },
  '/progress': {
    title: 'Progression',
    subtitle: 'Tendances multi-activités',
    container: 'default',
    showToday: true,
  },
  '/goals': {
    title: 'Objectifs',
    subtitle: 'Courses et trails à venir',
    container: 'default',
    showToday: true,
  },
  '/traces': {
    title: 'Traces GPX',
    subtitle: 'Bibliotheque des traces enregistrees',
    container: 'default',
    showToday: true,
  },
  '/settings': {
    title: 'Paramètres',
    subtitle: 'Configuration de l’application',
    container: 'default',
    HeaderActions: SettingsHeaderVersion,
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

function isDynamicRealActivityRoute(pathname: string) {
  return /^\/activities\/[^/]+$/.test(pathname);
}

function isDynamicTraceRoute(pathname: string) {
  return /^\/traces\/[^/]+$/.test(pathname);
}

export function resolvePageMetadata(pathname: string): PageMetadata {
  const normalizedPathname = normalizePathname(pathname);

  if (isDynamicRealActivityRoute(normalizedPathname)) {
    return {
      title: 'Activité',
      subtitle: 'Analyse réelle',
      container: 'wide',
      showToday: true,
    };
  }

  if (isDynamicTraceRoute(normalizedPathname)) {
    return {
      title: 'Trace',
      subtitle: 'Analyse théorique',
      container: 'wide',
      showToday: true,
    };
  }

  return STATIC_PAGE_METADATA[normalizedPathname] ?? FALLBACK_PAGE_METADATA;
}
