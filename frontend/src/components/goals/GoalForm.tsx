'use client';

import * as React from 'react';
import { Flag } from 'lucide-react';

import { CityAutocomplete } from '@/components/inputs/CityAutocomplete';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { parseFlexibleSeconds, formatPaceInputFromSeconds, formatTimeInputFromSeconds } from '@/lib/paceUtils';
import type { GoalItem, GeoCityItem } from '@/types/api';
import { type GoalFormState, type GoalMode, INITIAL_FORM } from '@/components/goals/utils';

type GoalFormProps = {
  isOpen: boolean;
  editingGoal: GoalItem | null;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (payload: any) => Promise<void>;
};

export function GoalForm({ isOpen, editingGoal, isSubmitting, onClose, onSubmit }: GoalFormProps) {
  const [form, setForm] = React.useState<GoalFormState>(INITIAL_FORM);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [selectedCity, setSelectedCity] = React.useState<GeoCityItem | null>(null);
  const [locationNeedsSelection, setLocationNeedsSelection] = React.useState(false);

  const isEditing = editingGoal !== null;

  React.useEffect(() => {
    if (!isOpen) {
      setForm(INITIAL_FORM);
      setFormError(null);
      setSelectedCity(null);
      setLocationNeedsSelection(false);
      return;
    }
    if (editingGoal) {
      const goal = editingGoal;
      const isTimeGoal = typeof goal.target_time_s === 'number' && Number.isFinite(goal.target_time_s);
      const targetTime = isTimeGoal ? formatTimeInputFromSeconds(goal.target_time_s as number) : '01:00:00';
      const paceSeconds = typeof goal.target_pace_s_per_km === 'number' && Number.isFinite(goal.target_pace_s_per_km) ? goal.target_pace_s_per_km : 300;

      setForm({
        name: goal.name,
        eventDate: String(goal.event_date).slice(0, 10),
        distanceKm: String(goal.distance_km),
        location: goal.location ?? '',
        mode: isTimeGoal ? 'time' : 'pace',
        targetPace: formatPaceInputFromSeconds(paceSeconds),
        targetTime,
        raceType: goal.race_type,
        notes: goal.notes ?? '',
      });
      setSelectedCity(
        goal.location_city && goal.location_country && typeof goal.location_lat === 'number' && typeof goal.location_lon === 'number'
          ? {
              label: goal.location ?? `${goal.location_city}, ${goal.location_country}`,
              city: goal.location_city,
              country: goal.location_country,
              country_code: goal.location_country_code ?? null,
              lat: goal.location_lat,
              lon: goal.location_lon,
            }
          : null
      );
    }
  }, [isOpen, editingGoal]);

  if (!isOpen) return null;

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    const name = form.name.trim();
    const eventDate = form.eventDate.trim();
    const distanceKm = Number(form.distanceKm);
    if (!name) {
      setFormError('Le nom de la course est requis.');
      return;
    }
    if (!eventDate) {
      setFormError('La date est requise.');
      return;
    }
    if (!Number.isFinite(distanceKm) || distanceKm <= 0) {
      setFormError('La distance doit être un nombre > 0.');
      return;
    }

    const payload: Record<string, unknown> = {
      name,
      event_date: eventDate,
      distance_km: distanceKm,
      race_type: form.raceType,
    };

    const location = form.location.trim();
    if (location && locationNeedsSelection && selectedCity === null) {
      setFormError('Selectionne une ville dans la liste de suggestions.');
      return;
    }
    if (location) payload.location = location;
    if (selectedCity) {
      payload.location_city = selectedCity.city;
      payload.location_country = selectedCity.country;
      payload.location_country_code = selectedCity.country_code ?? undefined;
      payload.location_lat = selectedCity.lat;
      payload.location_lon = selectedCity.lon;
    }
    const notes = form.notes.trim();
    if (notes) payload.notes = notes;

    if (form.mode === 'time') {
      const seconds = parseFlexibleSeconds(form.targetTime);
      if (seconds === null || seconds <= 0) {
        setFormError('Temps objectif invalide (format hh:mm:ss, mm:ss ou minutes).');
        return;
      }
      payload.target_time_s = seconds;
    } else {
      const seconds = parseFlexibleSeconds(form.targetPace);
      if (seconds === null || seconds < 120 || seconds > 1200) {
        setFormError('Allure objectif invalide (entre 2:00 et 20:00 /km).');
        return;
      }
      payload.target_pace_s_per_km = seconds;
    }

    await onSubmit(payload);
  };

  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-base flex items-center gap-2">
          <Flag className="h-4 w-4" />
          {isEditing ? 'Modifier un objectif' : 'Nouvel objectif'}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <label className="text-sm">
              <div className="text-muted-foreground">Nom</div>
              <input
                className="mt-1 h-9 w-full rounded-md border px-3"
                value={form.name}
                onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Marathon de Paris"
              />
            </label>

            <label className="text-sm">
              <div className="text-muted-foreground">Date</div>
              <input
                type="date"
                className="mt-1 h-9 w-full rounded-md border px-3"
                value={form.eventDate}
                onChange={(e) => setForm((prev) => ({ ...prev, eventDate: e.target.value }))}
              />
            </label>

            <label className="text-sm">
              <div className="text-muted-foreground">Distance (km)</div>
              <input
                type="number"
                step="0.1"
                className="mt-1 h-9 w-full rounded-md border px-3"
                value={form.distanceKm}
                onChange={(e) => setForm((prev) => ({ ...prev, distanceKm: e.target.value }))}
                placeholder="42.2"
              />
            </label>

            <label className="text-sm">
              <div className="text-muted-foreground">Localisation</div>
              <CityAutocomplete
                className="h-9 w-full rounded-md border px-3"
                value={form.location}
                onChange={(next) => {
                  setForm((prev) => ({ ...prev, location: next }));
                  setLocationNeedsSelection(next.trim().length > 0);
                }}
                onSelectionChange={(item) => {
                  setSelectedCity(item);
                  setLocationNeedsSelection(item === null && form.location.trim().length > 0);
                }}
                placeholder="Ville, Pays"
              />
            </label>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <label className="text-sm">
              <div className="text-muted-foreground">Type de course</div>
              <select
                className="mt-1 h-9 w-full rounded-md border bg-background px-3"
                value={form.raceType}
                onChange={(e) => setForm((prev) => ({ ...prev, raceType: e.target.value as 'road' | 'trail' }))}
              >
                <option value="road">Course à pied</option>
                <option value="trail">Trail</option>
              </select>
            </label>

            <label className="text-sm">
              <div className="text-muted-foreground">Objectif principal</div>
              <select
                className="mt-1 h-9 w-full rounded-md border bg-background px-3"
                value={form.mode}
                onChange={(e) => setForm((prev) => ({ ...prev, mode: e.target.value as GoalMode }))}
              >
                <option value="time">Temps cible</option>
                <option value="pace">Allure cible</option>
              </select>
            </label>

            {form.mode === 'time' ? (
              <label className="text-sm md:col-span-2 xl:col-span-2">
                <div className="text-muted-foreground">Temps cible</div>
                <input
                  className="mt-1 h-9 w-full rounded-md border px-3"
                  value={form.targetTime}
                  onChange={(e) => setForm((prev) => ({ ...prev, targetTime: e.target.value }))}
                  placeholder="03:30:00"
                />
              </label>
            ) : (
              <label className="text-sm md:col-span-2 xl:col-span-2">
                <div className="text-muted-foreground">Allure cible (/km)</div>
                <input
                  className="mt-1 h-9 w-full rounded-md border px-3"
                  value={form.targetPace}
                  onChange={(e) => setForm((prev) => ({ ...prev, targetPace: e.target.value }))}
                  placeholder="4:45"
                />
              </label>
            )}
          </div>

          <label className="block text-sm">
            <div className="text-muted-foreground">Notes (optionnel)</div>
            <textarea
              className="mt-1 min-h-20 w-full rounded-md border px-3 py-2"
              value={form.notes}
              onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))}
              placeholder="Plan nutrition, stratégie de course, etc."
            />
          </label>

          {formError ? <div className="text-sm text-red-600">{formError}</div> : null}

          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Annuler
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Enregistrement...' : isEditing ? 'Enregistrer les modifications' : 'Enregistrer l’objectif'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
