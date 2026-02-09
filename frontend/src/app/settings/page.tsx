'use client';

import * as React from 'react';
import Link from 'next/link';
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
import { Activity, Save, Settings } from 'lucide-react';

const PERSIST_UPLOADS_KEY = 'coursescope.persist_uploads_to_disk';

function getPersistUploads(): boolean {
  if (typeof window === 'undefined') return false;
  const raw = window.localStorage.getItem(PERSIST_UPLOADS_KEY);
  if (raw === null) return false;
  return raw === 'true';
}

function setPersistUploads(next: boolean) {
  window.localStorage.setItem(PERSIST_UPLOADS_KEY, next ? 'true' : 'false');
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [persistUploadsToDisk, setPersistUploadsToDisk] = React.useState(false);

  React.useEffect(() => {
    setPersistUploadsToDisk(getPersistUploads());
  }, []);

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

  const saveCreds = useMutation<GarminCredentialsStatusResponse, Error, { email: string; password: string }>({
    mutationFn: (payload) => garminApi.saveCredentials(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['garmin', 'credentials'] });
    },
  });

  const connect = useMutation<GarminConnectResponse, Error, { email?: string; password?: string; otp?: string | null }>({
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

  return (
    <div className="container mx-auto py-6 px-4 max-w-4xl">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs text-muted-foreground">CourseScope</div>
          <h1 className="text-2xl font-bold truncate">Parametres</h1>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/">
              <Activity className="h-4 w-4 mr-2" />
              Accueil
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/activities">Historique</Link>
          </Button>
        </div>
      </div>

      <div className="mt-6 space-y-4">
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
                <Button size="sm" variant="outline" onClick={() => garminStatus.refetch()} disabled={garminStatus.isFetching}>
                  Rafraichir
                </Button>
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
                  <div className="text-xs text-muted-foreground break-all">{garminStatus.data.tokens_dir}</div>
                  <div>
                    Cursor sync: <span className="font-medium">{garminStatus.data.cursor_time_utc ?? '—'}</span>
                  </div>
                  {garminStatus.data.last_run ? (
                    <div className="text-xs text-muted-foreground">
                      Derniere sync: {garminStatus.data.last_run.status} • +{garminStatus.data.last_run.imported_count} / skip {garminStatus.data.last_run.skipped_count}
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
                <label className="text-sm">
                  <div className="text-muted-foreground">OTP (si MFA)</div>
                  <input
                    className="mt-1 w-full rounded-md border px-3 py-2"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="123456"
                    inputMode="numeric"
                  />
                </label>
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
                    onClick={() => connect.mutate({ email, password, otp: otp.trim() ? otp.trim() : null })}
                    disabled={connect.isPending || email.trim().length === 0 || password.length === 0}
                  >
                    Connecter
                  </Button>
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => connect.mutate({})} disabled={connect.isPending}>
                Connecter (cred stockes)
              </Button>
              <Button size="sm" onClick={() => sync.mutate()} disabled={sync.isPending}>
                Sync
              </Button>
            </div>

            {sync.data ? (
              <div className="text-sm text-muted-foreground">
                Sync: {sync.data.status} • +{sync.data.imported_count} / skip {sync.data.skipped_count}
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
