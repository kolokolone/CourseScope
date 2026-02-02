# climbs (Montees detectees)

Ce document decrit la logique backend utilisee pour la section "Montees detectees" (payload `climbs.items`).

## Source

- Calcul: `backend/core/real_run_analysis.py:compute_climbs`
- Integration: `backend/services/real_activity_service.py:prepare_base`
- Exposition API: `backend/api/routes/analysis.py:prepare_real_response` (champ `climbs`)

## Donnees d'entree (DataFrame)

Colonnes requises (unites):
- `distance_m` (m)
- `delta_distance_m` (m)
- `elevation` (m)
- `delta_time_s` (s)
- `pace_s_per_km` (s/km)

## Objectif

Detecter des segments de montee de facon robuste, en evitant:
- la sur-segmentation (replats/variations courtes)
- le bruit altitude (GPS/baro)

## Algorithme (v1.1.46+)

1) Grille distance (resampling)
- Construction d'une grille reguliere en distance (step ~ 5m).
- Interpolation de l'altitude et du "moving time" sur cette grille.

2) Lissage altitude (en distance)
- Lissage par moyenne glissante sur ~25m (fenetre en metres, pas en nombre de points).

3) Pente robuste (fenetre distance)
- Pente calculee sur une fenetre de distance (ex: 50m):
  - `grade[%] = 100 * (elev_smooth[i] - elev_smooth[i-lag]) / window_m`

4) Detection (machine d'etat)
- Start: `grade >= 3%` sur une distance minimale (ex: 20m)
- Continue: `grade >= 1%`
- Gap bridging: replats tolérés tant que `grade >= 0.2%` et que le gap reste court (distance et/ou temps)
- Stop: gap trop long, ou descente nette (`grade <= -1%` sur >= 30m)

5) Metriques sur segment complet
- Distance: `distance_m[end] - distance_m[start]`
- D+: somme des increments positifs sur l'altitude lissee
- Pente moyenne: `D+ / distance * 100`
- VAM: `D+ / duree * 3600` (duree = moving time, pauses exclues)
- Allure: mediane de `pace_s_per_km` sur le segment

## Output (contrat API conserve)

Chaque item renvoye conserve les champs attendus par le frontend:
- `distance_km`
- `elevation_gain_m`
- `avg_grade_percent`
- `pace_s_per_km`
- `vam_m_h`
- `start_idx`, `end_idx`
- `distance_m_end`

Champs additionnels (optionnels, UI):
- `start_km`, `end_km`
- `start_end_km` (string avec centiemes)
- `duration_s` (moving time)

Les items sont tries par `elevation_gain_m` (descendant). Aucun "top 3" n'est force: le frontend affiche la liste telle quelle.
