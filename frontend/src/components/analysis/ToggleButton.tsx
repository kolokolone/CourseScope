import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export function ToggleButton({ active, children, className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return <button {...props} className={cn('rounded-md px-2.5 py-1.5 text-xs font-medium transition', active ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-background text-muted-foreground ring-1 ring-inset ring-border hover:bg-muted hover:text-foreground', className)}>{children}</button>;
}
