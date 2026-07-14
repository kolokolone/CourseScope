import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

export function AnalysisCard({ title, description, actions, children, className, id }: { title?: string; description?: string; actions?: ReactNode; children: ReactNode; className?: string; id?: string }) {
  return (
    <section id={id} className={cn('scroll-mt-24 rounded-2xl border border-border bg-card text-card-foreground shadow-sm', className)}>
      {title || description || actions ? (
        <header className="flex flex-col gap-3 border-b border-border px-5 py-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            {title ? <h2 className="text-base font-semibold tracking-tight">{title}</h2> : null}
            {description ? <p className="mt-1 text-sm leading-5 text-muted-foreground">{description}</p> : null}
          </div>
          {actions ? <div className="shrink-0">{actions}</div> : null}
        </header>
      ) : null}
      <div className="p-5">{children}</div>
    </section>
  );
}
