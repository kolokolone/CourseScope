import type { ProgressIndexStatusResponse } from '@/types/api';

type ProgressIndexationBannerProps = {
  state: ProgressIndexStatusResponse | null;
};

export function ProgressIndexationBanner({ state }: ProgressIndexationBannerProps) {
  if (!state) return null;

  return (
    <>
      {state.running ? (
        <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Indexation {state.mode === 'slow' ? 'complete' : 'rapide'} en cours: les graphes peuvent etre incomplets pendant quelques secondes.
        </div>
      ) : null}

      {!state.running && state.last_error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          Echec de l indexation: {state.last_error}
        </div>
      ) : null}
    </>
  );
}
