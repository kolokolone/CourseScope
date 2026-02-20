import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';

type TopHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  contextInfo?: React.ReactNode;
  onOpenSidebar: () => void;
};

export function TopHeader({ title, subtitle, actions, contextInfo, onOpenSidebar }: TopHeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/85">
      <div className="mx-auto flex w-full max-w-[88rem] items-start justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-9 w-9 md:hidden"
              onClick={onOpenSidebar}
              aria-label="Ouvrir la navigation"
            >
              <Menu className="h-4 w-4" />
            </Button>
            <h1 className="truncate text-2xl font-semibold tracking-tight">{title}</h1>
          </div>
          {subtitle ? <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p> : null}
        </div>

        <div className="flex shrink-0 self-center items-center gap-2">
          {contextInfo ? <span className="hidden text-xs text-muted-foreground sm:inline">{contextInfo}</span> : null}
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </div>
      </div>
    </header>
  );
}
