import { Button } from '@/components/ui/button';

type BetaErrorProps = {
  message?: string;
  onRetry: () => void;
  onBack: () => void;
};

export function BetaError({ message, onRetry, onBack }: BetaErrorProps) {
  return (
    <div className="py-12 text-center">
      <div className="text-red-600 text-lg font-semibold mb-2">
        Impossible de charger l'activité
      </div>
      <p className="text-sm text-slate-500 mb-6">
        {message || 'Une erreur est survenue lors du chargement des données.'}
      </p>
      <div className="flex justify-center gap-3">
        <Button onClick={onRetry}>Réessayer</Button>
        <Button variant="outline" onClick={onBack}>
          Retour aux activités
        </Button>
      </div>
    </div>
  );
}
