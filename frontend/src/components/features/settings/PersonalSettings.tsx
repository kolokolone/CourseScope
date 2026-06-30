'use client';

import * as React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useDetectedHrMax, usePatchPersonalSettings, usePersonalSettings } from '@/hooks/useSettings';

function normalizeDecimalInput(value: string): string {
  return value.replace(',', '.').trim();
}

function parseOptionalInt(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed.length === 0) return null;
  const n = Number(trimmed);
  if (!Number.isFinite(n)) return null;
  return Math.round(n);
}

export function PersonalSettings() {
  const personalSettingsQuery = usePersonalSettings();
  const detectedHrQuery = useDetectedHrMax();
  const patchPersonalMutation = usePatchPersonalSettings();

  const [vmaInput, setVmaInput] = React.useState('');
  const [manualHrInput, setManualHrInput] = React.useState('');
  const [hrSource, setHrSource] = React.useState<'detected' | 'manual'>('detected');
  const [personalMessage, setPersonalMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    const data = personalSettingsQuery.data;
    if (!data) return;
    setVmaInput(typeof data.vma_kmh === 'number' ? String(data.vma_kmh) : '');
    setManualHrInput(typeof data.hr_max_manual_bpm === 'number' ? String(data.hr_max_manual_bpm) : '');
    setHrSource(data.hr_max_source);
  }, [personalSettingsQuery.data]);

  const detectedHr =
    typeof detectedHrQuery.data?.hr_max_detected_bpm === 'number'
      ? detectedHrQuery.data.hr_max_detected_bpm
      : personalSettingsQuery.data?.hr_max_detected_bpm ?? null;

  const savePersonalSettings = async () => {
    setPersonalMessage(null);
    const normalizedVmaRaw = normalizeDecimalInput(vmaInput);
    const parsedVma = normalizedVmaRaw.length > 0 ? Number(normalizedVmaRaw) : null;
    if (parsedVma !== null && (!Number.isFinite(parsedVma) || parsedVma < 6 || parsedVma > 30)) {
      setPersonalMessage('VMA invalide (entre 6.0 et 30.0 km/h).');
      return;
    }

    const parsedManualHr = parseOptionalInt(manualHrInput);
    if (manualHrInput.trim().length > 0 && (parsedManualHr === null || parsedManualHr < 80 || parsedManualHr > 240)) {
      setPersonalMessage('FC max manuelle invalide (entre 80 et 240 bpm).');
      return;
    }

    try {
      await patchPersonalMutation.mutateAsync({
        vma_kmh: parsedVma,
        hr_max_manual_bpm: parsedManualHr,
        hr_max_source: hrSource,
      });
      setPersonalMessage('Parametres personnels enregistres.');
    } catch (err) {
      setPersonalMessage(`Erreur d'enregistrement: ${String(err)}`);
    }
  };

  const applyDetectedHr = async () => {
    if (typeof detectedHr !== 'number') return;
    setHrSource('detected');
    try {
      await patchPersonalMutation.mutateAsync({ hr_max_source: 'detected' });
      setPersonalMessage('Utilisation de la FC max detectee activee.');
    } catch (err) {
      setPersonalMessage(`Erreur: ${String(err)}`);
    }
  };

  return (
    <Card className="rounded-2xl border border-[var(--hairline)] bg-[var(--surface-card)]">
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-base">Donnees personnelles</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="text-sm">
            <div className="text-muted-foreground">VMA estimee (km/h)</div>
            <input
              className="mt-1 w-full rounded-md border px-3 py-2"
              inputMode="decimal"
              placeholder="16.0"
              value={vmaInput}
              onChange={(e) => setVmaInput(e.target.value)}
              onBlur={(e) => {
                const n = Number(normalizeDecimalInput(e.target.value));
                if (Number.isFinite(n)) setVmaInput(String(Math.round(n * 10) / 10));
              }}
            />
            <div className="mt-1 text-xs text-muted-foreground">
              Utilise pour calculer l&apos;allure theorique selon la pente.
            </div>
          </label>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2 text-sm">
            <div className="text-muted-foreground">FC max detectee</div>
            <div className="flex items-center gap-2">
              <div className="font-medium tabular-nums">{typeof detectedHr === 'number' ? `${detectedHr} bpm` : 'Aucune detection'}</div>
              <Button size="sm" variant="outline" onClick={applyDetectedHr} disabled={typeof detectedHr !== 'number' || patchPersonalMutation.isPending}>
                Utiliser
              </Button>
            </div>
            <div className="text-xs text-muted-foreground">
              Source active: <span className="font-medium">{hrSource === 'detected' ? 'detectee' : 'manuelle'}</span>
            </div>
          </div>

          <label className="text-sm">
            <div className="text-muted-foreground">FC max manuelle (bpm)</div>
            <input
              className="mt-1 w-full rounded-md border px-3 py-2"
              inputMode="numeric"
              placeholder="190"
              value={manualHrInput}
              onChange={(e) => setManualHrInput(e.target.value)}
            />
          </label>

          <label className="text-sm">
            <div className="text-muted-foreground">Source FC max</div>
            <select
              className="mt-1 h-10 w-full rounded-md border bg-background px-3"
              value={hrSource}
              onChange={(e) => setHrSource(e.target.value as 'detected' | 'manual')}
            >
              <option value="detected">Detectee</option>
              <option value="manual">Manuelle</option>
            </select>
          </label>
        </div>

        <div className="flex items-center gap-2">
          <Button size="sm" onClick={savePersonalSettings} disabled={patchPersonalMutation.isPending || personalSettingsQuery.isLoading}>
            Enregistrer
          </Button>
          {personalMessage ? <div className="text-sm text-muted-foreground">{personalMessage}</div> : null}
        </div>
      </CardContent>
    </Card>
  );
}
