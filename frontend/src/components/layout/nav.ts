import type { LucideIcon } from 'lucide-react';
import { ChartNoAxesCombined, Home, ListChecks, Route, Settings, Target } from 'lucide-react';

export type NavPlacement = 'main' | 'footer';

export type NavItemConfig = {
  label: string;
  href: string;
  icon: LucideIcon;
  placement: NavPlacement;
};

export const NAV_ITEMS: NavItemConfig[] = [
  {
    label: 'Page d’accueil',
    href: '/',
    icon: Home,
    placement: 'main',
  },
  {
    label: 'Activités',
    href: '/activities',
    icon: ListChecks,
    placement: 'main',
  },
  {
    label: 'Progression',
    href: '/progress',
    icon: ChartNoAxesCombined,
    placement: 'main',
  },
  {
    label: 'Objectifs',
    href: '/goals',
    icon: Target,
    placement: 'main',
  },
  {
    label: 'Traces GPX',
    href: '/traces',
    icon: Route,
    placement: 'main',
  },
  {
    label: 'Paramètres',
    href: '/settings',
    icon: Settings,
    placement: 'footer',
  },
];

export const MAIN_NAV_ITEMS = NAV_ITEMS.filter((item) => item.placement === 'main');
export const FOOTER_NAV_ITEMS = NAV_ITEMS.filter((item) => item.placement === 'footer');
