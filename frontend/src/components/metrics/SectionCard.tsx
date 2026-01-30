import type { ReactNode } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export function SectionCard({
  title,
  description,
  children,
  testId,
  accentColor,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  testId?: string;
  accentColor?: string;
}) {
  return (
    <Card
      data-testid={testId}
      className={cn(accentColor ? 'border-l-4' : undefined)}
      style={accentColor ? { borderLeftColor: accentColor } : undefined}
    >
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
