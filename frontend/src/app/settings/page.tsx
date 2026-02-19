'use client';

import * as React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { garminApi } from '@/lib/api';
import type {
  GarminConnectResponse,
  GarminCredentialsStatusResponse,
  GarminStatusResponse,
  GarminSyncResponse,
} from '@/types/api';
import { Save, Settings, Trash2 } from 'lucide-react';
import { useCleanupActivities } from '@/hooks/useActivity';
import { useDetectedHrMax, usePatchPersonalSettings, usePersonalSettings } from '@/hooks/useSettings';

const PERSIST_UPLOADS_KEY = 'coursescope.persist_uploads_to_disk';

function formatIsoUtcFr(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return iso;
  const date = d.toLocaleDateString('fr-FR', { timeZone: 'UTC' });
  const time = d.toLocaleTimeString('fr-FR', {
    timeZone: 'UTC',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
  return `${date} ${time}`;
}

function formatSyncDelta(importedCount: number, skippedCount: number): string {
  const imported = Number.isFinite(importedCount) ? importedCount : 0;
  const skipped = Number.isFinite(skippedCount) ? skippedCount : 0;
  return `+${imported} activites ajoutees (${skipped} activites evitees)`;
}

function getPersistUploads(): boolean {
  if (typeof window === 'undefined') return false;
  const raw = window.localStorage.getItem(PERSIST_UPLOADS_KEY);
  if (raw === null) return false;
  return raw === 'true';
}

function setPersistUploads(next: boolean) {
  window.localStorage.setItem(PERSIST_UPLOADS_KEY, next ? 'true' : 'false');
}

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

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [persistUploadsToDisk, setPersistUploadsToDisk] = React.useState(false);
  const personalSettingsQuery = usePersonalSettings();
  const detectedHrQuery = useDetectedHrMax();
  const patchPersonalMutation = usePatchPersonalSettings();

  const [vmaInput, setVmaInput] = React.useState('');
  const [manualHrInput, setManualHrInput] = React.useState('');
  const [hrSource, setHrSource] = React.useState<'detected' | 'manual'>('detected');
  const [personalMessage, setPersonalMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    setPersistUploadsToDisk(getPersistUploads());
  }, []);

  React.useEffect(() => {
    const data = personalSettingsQuery.data;
    if (!data) return;
    setVmaInput(typeof data.vma_kmh === 'number' ? String(data.vma_kmh) : '');
    setManualHrInput(typeof data.hr_max_manual_bpm === 'number' ? String(data.hr_max_manual_bpm) : '');
    setHrSource(data.hr_max_source);
  }, [personalSettingsQuery.data]);

  const garminStatus = useQuery<GarminStatusResponse>({
    queryKey: ['garmin', 'status'],
    queryFn: () => garminApi.status(),
    staleTime: 10_000,
  });

  const credsStatus = useQuery<GarminCredentialsStatusResponse>({
    queryKey: ['garmin', 'credentials', 'status'],
    queryFn: () => garminApi.credentialsStatus(),
    staleTime: 10_000,
  });

  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [otp, setOtp] = React.useState('');
  const [mfaSessionId, setMfaSessionId] = React.useState<string | null>(null);
  const [otpStep, setOtpStep] = React.useState(false);

  const saveCreds = useMutation<GarminCredentialsStatusResponse, Error, { email: string; password: string }>({
    mutationFn: (payload) => garminApi.saveCredentials(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['garmin', 'credentials'] });
    },
  });

  const connect = useMutation<GarminConnectResponse, Error, { email?: string; password?: string; otp?: string | null; mfa_session_id?: string | null }>({
    mutationFn: (payload) => garminApi.connect(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['garmin', 'status'] });
    },
  });

  const sync = useMutation<GarminSyncResponse, Error, void>({
    mutationFn: () => garminApi.sync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['garmin', 'status'] });
    },
  });

  const fullSync = useMutation({
    mutationFn: async () => {
      await garminApi.reset();
      return garminApi.sync();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['garmin', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['activities'] });
    },
  });

  const cleanupMutation = useCleanupActivities();

  const handleCleanup = async () => {
    if (window.confirm('Supprimer toutes les activites sur disque ?')) {
      try {
        await cleanupMutation.mutateAsync();
        queryClient.invalidateQueries({ queryKey: ['activities'] });
      } catch {
        alert('Failed to cleanup activities');
      }
    }
  };

  const startConnect = async (payload: { email?: string; password?: string }) => {
    setOtp('');
    setOtpStep(false);
    setMfaSessionId(null);
    const res = await connect.mutateAsync(payload);
    if (res.status === 'otp_required') {
      setOtpStep(true);
      setMfaSessionId(res.mfa_session_id ?? null);
    } else {
      setOtpStep(false);
      setMfaSessionId(null);
    }
  };

  const confirmOtp = async () => {
    if (!mfaSessionId) return;
    const code = otp.trim();
    if (!code) return;
    await connect.mutateAsync({ otp: code, mfa_session_id: mfaSessionId } as unknown as { otp?: string | null; mfa_session_id?: string | null });
    setOtpStep(false);
    setMfaSessionId(null);
    setOtp('');
  };

  const canConnectWithTyped = email.trim().length > 0 && password.length > 0;
  const canConnectWithStored = Boolean(credsStatus.data?.configured);
  const connectLabel = canConnectWithTyped ? 'Connecter' : 'Connecter (cred stockes)';

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
    <div className="space-y-4">
      <Card>
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
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-base flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Upload
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <label className="flex items-center justify-between gap-3">
            <div>
              <div className="font-medium">Enregistrer les uploads sur disque</div>
              <div className="text-sm text-muted-foreground">
                Par defaut: OFF. Si OFF, l'analyse reste disponible tant que le backend tourne (pas d'historique).
              </div>
            </div>
            <input
              type="checkbox"
              className="h-5 w-5"
              checked={persistUploadsToDisk}
              onChange={(e) => {
                const next = e.target.checked;
                setPersistUploads(next);
                setPersistUploadsToDisk(next);
              }}
            />
          </label>

          <div className="mt-4">
            <Button
              size="sm"
              variant="outline"
              onClick={handleCleanup}
              disabled={cleanupMutation.isPending}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Cleanup activites
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-base">Garmin</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-4">
          <div className="rounded-md border p-3 text-sm">
            <div className="flex items-center justify-between gap-3">
              <div className="font-medium">Statut</div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => garminStatus.refetch()} disabled={garminStatus.isFetching}>
                  Rafraichir
                </Button>
                <Button size="sm" onClick={() => sync.mutate()} disabled={sync.isPending}>
                  Sync
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={async () => {
                    if (!window.confirm('Relancer une synchronisation complete Garmin ?')) return;
                    fullSync.mutate();
                  }}
                  disabled={fullSync.isPending}
                  title="Reset cursor + relance sync"
                >
                  Sync complet
                </Button>
              </div>
            </div>

            {garminStatus.isLoading ? (
              <div className="text-muted-foreground mt-2">Chargement...</div>
            ) : garminStatus.isError ? (
              <div className="text-red-600 mt-2">Erreur: {String(garminStatus.error)}</div>
            ) : garminStatus.data ? (
              <div className="mt-2 space-y-1">
                <div>
                  Tokens: <span className="font-medium">{garminStatus.data.tokens_present ? 'OK' : 'absents'}</span>
                </div>
                <div>
                  Cursor sync: <span className="font-medium">{formatIsoUtcFr(garminStatus.data.cursor_time_utc)}</span>
                </div>
                {garminStatus.data.cursor_updated_at_utc ? (
                  <div className="text-xs text-muted-foreground">
                    Maj cursor: {formatIsoUtcFr(garminStatus.data.cursor_updated_at_utc)}
                  </div>
                ) : null}
                {garminStatus.data.last_run ? (
                  <div className="text-xs text-muted-foreground">
                    Derniere sync: {formatIsoUtcFr(garminStatus.data.last_run.finished_at_utc ?? garminStatus.data.last_run.started_at_utc)} • {garminStatus.data.last_run.status} • {formatSyncDelta(garminStatus.data.last_run.imported_count, garminStatus.data.last_run.skipped_count)}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="rounded-md border p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="font-medium">Identifiants</div>
                <div className="text-sm text-muted-foreground">Stockes localement sur disque (exclus de git).</div>
              </div>
              <Button size="sm" variant="outline" onClick={() => credsStatus.refetch()} disabled={credsStatus.isFetching}>
                Verifier
              </Button>
            </div>

            {credsStatus.data ? (
              <div className="mt-2 text-sm">
                Configure: <span className="font-medium">{credsStatus.data.configured ? 'oui' : 'non'}</span>
                {credsStatus.data.email ? <span className="text-muted-foreground"> • {credsStatus.data.email}</span> : null}
                <div className="text-xs text-muted-foreground break-all">{credsStatus.data.path}</div>
              </div>
            ) : null}

            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="text-sm">
                <div className="text-muted-foreground">Email</div>
                <input
                  className="mt-1 w-full rounded-md border px-3 py-2"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="email@example.com"
                  autoComplete="username"
                />
              </label>
              <label className="text-sm">
                <div className="text-muted-foreground">Mot de passe</div>
                <input
                  className="mt-1 w-full rounded-md border px-3 py-2"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  type="password"
                  autoComplete="current-password"
                />
              </label>
              {otpStep ? (
                <label className="text-sm">
                  <div className="text-muted-foreground">OTP</div>
                  <input
                    className="mt-1 w-full rounded-md border px-3 py-2"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="123456"
                    inputMode="numeric"
                  />
                </label>
              ) : null}
              <div className="flex items-end gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => saveCreds.mutate({ email, password })}
                  disabled={saveCreds.isPending || email.trim().length === 0 || password.length === 0}
                >
                  <Save className="h-4 w-4 mr-2" />
                  Enregistrer
                </Button>
                <Button
                  size="sm"
                  onClick={() => startConnect(canConnectWithTyped ? { email, password } : {})}
                  disabled={connect.isPending || otpStep || (!canConnectWithTyped && !canConnectWithStored)}
                >
                  {connectLabel}
                </Button>
                {otpStep ? (
                  <Button
                    size="sm"
                    onClick={confirmOtp}
                    disabled={connect.isPending || otp.trim().length === 0 || !mfaSessionId}
                  >
                    Confirmer
                  </Button>
                ) : null}
              </div>
            </div>
          </div>

          {sync.data ? (
            <div className="text-sm text-muted-foreground">
              Sync: {sync.data.status} • {formatSyncDelta(sync.data.imported_count, sync.data.skipped_count)}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
