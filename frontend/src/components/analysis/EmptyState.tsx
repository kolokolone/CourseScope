export function EmptyState({ message }: { message: string }) {
  return <div className="rounded-xl border border-dashed border-border bg-muted/30 px-4 py-6 text-sm text-muted-foreground">{message}</div>;
}
