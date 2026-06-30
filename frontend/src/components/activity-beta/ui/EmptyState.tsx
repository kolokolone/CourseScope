type EmptyStateProps = {
  message: string;
};

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
      {message}
    </div>
  );
}
