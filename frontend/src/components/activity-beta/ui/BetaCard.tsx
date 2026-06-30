import { cn } from '@/lib/utils';

type BetaCardProps = {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
};

export function BetaCard({ title, description, actions, children, className }: BetaCardProps) {
  return (
    <section className={cn('rounded-2xl border border-slate-200 bg-white shadow-sm', className)}>
      {(title || description || actions) && (
        <header className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            {title && <h2 className="text-base font-semibold tracking-tight text-slate-950">{title}</h2>}
            {description && <p className="mt-1 text-sm leading-5 text-slate-500">{description}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}
