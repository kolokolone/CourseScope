import { cn } from '@/lib/utils';

export type ContainerVariant = 'default' | 'wide';

type PageContainerProps = {
  children: React.ReactNode;
  variant?: ContainerVariant;
  className?: string;
};

export function PageContainer({ children, variant = 'default', className }: PageContainerProps) {
  return (
    <div
      className={cn(
        'mx-auto w-full px-4 py-6 sm:px-6 lg:px-8',
        variant === 'wide' ? 'max-w-[88rem]' : 'max-w-6xl',
        className
      )}
    >
      {children}
    </div>
  );
}
