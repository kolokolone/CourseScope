import { cn } from '@/lib/utils';

type ToggleButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  active?: boolean;
};

export function ToggleButton({ active, children, className, ...props }: ToggleButtonProps) {
  return (
    <button
      {...props}
      className={cn(
        'rounded-md px-2.5 py-1.5 text-xs font-medium transition',
        active
          ? 'bg-blue-950 text-white shadow-sm'
          : 'bg-white text-slate-600 ring-1 ring-inset ring-slate-200 hover:bg-slate-50 hover:text-slate-950',
        className
      )}
    >
      {children}
    </button>
  );
}
