import type { ReactNode } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export function SectionCard({
  title,
  description,
  children,
  testId,
  accentColor,
  density = 'default',
  className,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  testId?: string;
  accentColor?: string;
  density?: 'default' | 'compact';
  className?: string;
}) {
  const headerClassName = density === 'compact' ? 'py-3 px-4' : undefined;
  const contentClassName = density === 'compact' ? 'px-4 pb-4' : undefined;
  const titleClassName = density === 'compact' ? 'text-base' : 'text-lg';

  return (
    <Card
      data-testid={testId}
      className={cn(accentColor ? 'border-l-4' : undefined, className)}
      style={accentColor ? { borderLeftColor: accentColor } : undefined}
    >
      <CardHeader className={headerClassName}>
        <CardTitle className={titleClassName}>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent className={contentClassName}>{children}</CardContent>
    </Card>
  );
}
