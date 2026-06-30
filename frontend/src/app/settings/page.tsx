'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PersonalSettings } from '@/components/features/settings/PersonalSettings';
import { GarminSettings } from '@/components/features/settings/GarminSettings';
import { MaintenanceSettings } from '@/components/features/settings/MaintenanceSettings';

export default function SettingsPage() {
  return (
    <div className="-mx-6 -mt-8 lg:-mx-8">
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8 space-y-8">
        <h1 className="display-lg text-[var(--ink)]">Parametres</h1>
        <PersonalSettings />
        <GarminSettings />
        <MaintenanceSettings />

        <Card className="rounded-2xl border border-[var(--hairline)] bg-[var(--surface-card)]">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-base">Mentions personnelles</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-3 text-sm">
            <div className="text-muted-foreground">
              Je m&apos;appelle Dominique Kolodziej et j&apos;ai cree CourseScope pour analyser et visualiser mes entrainements
              (traces, metriques, tendances) avec une approche claire et orientee performance.
            </div>

            <div className="text-muted-foreground">
              Le projet evolue en continu : si vous reperez un bug ou si vous avez une idee d&apos;amelioration, n&apos;hesitez pas a la
              partager via le depot GitHub.
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="link" asChild>
                <a href="https://github.com/kolokolone/CourseScope" target="_blank" rel="noreferrer">
                  Ouvrir le depot GitHub
                </a>
              </Button>

              <Button size="sm" variant="outline" disabled title="Bientot disponible">
                Offrir un cafe (bientot)
              </Button>
            </div>

            <div className="text-muted-foreground">
              Vous pourrez bientot m&apos;offrir un cafe pour soutenir le developpement du projet.
            </div>

            <div className="text-muted-foreground">
              Fait avec amour ❤️
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
