import { FOOTER_NAV_ITEMS, MAIN_NAV_ITEMS, type NavItemConfig } from './nav';
import { NavItem } from './NavItem';

type SidebarProps = {
  pathname: string;
  onNavigate?: () => void;
};

function isItemActive(pathname: string, item: NavItemConfig) {
  if (item.href === '/') return pathname === '/';
  if (item.href === '/activities' && pathname.startsWith('/activity/')) return true;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function Sidebar({ pathname, onNavigate }: SidebarProps) {
  return (
    <div className="flex h-full flex-col bg-card">
      <div className="border-b border-border px-5 py-5">
        <p className="text-lg font-semibold tracking-tight">CourseScope</p>
        <p className="mt-1 text-xs text-muted-foreground">Analyse d'activites de course</p>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4">
        <nav aria-label="Navigation principale" className="space-y-1">
          {MAIN_NAV_ITEMS.map((item) => (
            <NavItem key={item.href} item={item} isActive={isItemActive(pathname, item)} onNavigate={onNavigate} />
          ))}
        </nav>
      </div>

      <div className="border-t border-border px-3 py-4">
        <nav aria-label="Navigation secondaire" className="space-y-1">
          {FOOTER_NAV_ITEMS.map((item) => (
            <NavItem key={item.href} item={item} isActive={isItemActive(pathname, item)} onNavigate={onNavigate} />
          ))}
        </nav>
      </div>
    </div>
  );
}
