export function BetaSkeleton() {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-5">
        <div className="h-8 w-64 bg-slate-200 rounded-lg animate-pulse" />
        <div className="flex gap-2 mt-3">
          <div className="h-4 w-32 bg-slate-200 rounded animate-pulse" />
          <div className="h-4 w-24 bg-slate-200 rounded animate-pulse" />
        </div>
        <div className="mt-[18px] grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-[92px] bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>

      <div className="h-12 bg-slate-100 rounded-lg animate-pulse" />

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-5 h-48 bg-slate-100 rounded-2xl animate-pulse" />
        <div className="col-span-12 lg:col-span-7 h-48 bg-slate-100 rounded-2xl animate-pulse" />
      </div>

      <div className="h-72 animate-pulse rounded-2xl bg-slate-100 md:h-[420px]" />
      <div className="h-72 animate-pulse rounded-2xl bg-slate-100 md:h-[460px]" />
    </div>
  );
}
