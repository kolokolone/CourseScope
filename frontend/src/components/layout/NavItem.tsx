import Link from 'next/link';
import { cn } from '@/lib/utils';
import type { NavItemConfig } from './nav';

type NavItemProps = {
  item: NavItemConfig;
  isActive: boolean;
  onNavigate?: () => void;
};

export function NavItem({ item, isActive, onNavigate }: NavItemProps) {
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      className={cn(
        'group relative flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        isActive
          ? 'bg-accent text-foreground'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          'absolute inset-y-1 left-0 w-1 rounded-r-full transition-opacity',
          isActive ? 'bg-primary opacity-100' : 'bg-border opacity-0 group-hover:opacity-60'
        )}
      />
      <Icon className="h-5 w-5 shrink-0" />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}
