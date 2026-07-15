# Détection des montées (`climbs`)

> **Type** : Référence technique · **Endpoint** : `GET /activity/{id}/real` (champ `climbs`)
> **Dernière mise à jour** : v1.2.13

## Objectif

Décrire l'algorithme de détection des segments de montée utilisé par le backend, les données d'entrée, et le contrat de sortie API.

## Périmètre

Ce document couvre :
- L'algorithme de détection (machine d'état, lissage, gap bridging)
- Les métriques calculées par segment
- Le contrat API exposé au frontend

Ne couvre pas : l'affichage frontend (voir `docs/style-frontend-ui.md`).

## Source

- Calcul : `backend/core/real_run_analysis.py:compute_climbs`
- Intégration : `backend/services/real_activity_service.py:prepare_base`
- Exposition API : `backend/api/routes/analysis.py:prepare_real_response` (champ `climbs`)

## Données d'entrée (DataFrame)

Colonnes requises (unités) :
- `distance_m` (m)
- `delta_distance_m` (m)
- `elevation` (m)
- `delta_time_s` (s)
- `pace_s_per_km` (s/km)

## Algorithme

1) **Grille distance (resampling)**
   - Grille régulière en distance (step ~ 5 m)
   - Interpolation altitude et moving time sur cette grille

2) **Lissage altitude (en distance)**
   - Moyenne glissante sur ~25 m (fenêtre en mètres)

3) **Pente robuste (fenêtre distance)**
   - Pente calculée sur ~50 m : `grade[%] = 100 × (elev_smooth[i] - elev_smooth[i-lag]) / window_m`

4) **Détection (machine d'état)**
   - Start : `grade >= 3%` sur ≥ 20 m
   - Continue : `grade >= 1%`
   - Gap bridging : replats tolérés (`grade >= 0.2%`) tant que le gap est court
   - Stop : gap trop long ou descente (`grade <= -1%` sur ≥ 30 m)

5) **Métriques sur segment complet**
   - Distance : `distance_m[end] - distance_m[start]`
   - D+ : somme des incréments positifs d'altitude lissée
   - Pente moyenne : `D+ / distance × 100`
   - VAM : `D+ / durée × 3600` (durée = moving time)
   - Allure : médiane de `pace_s_per_km` sur le segment

## Contrat API

Chaque item renvoyé :

| Champ | Type | Description |
|---|---|---|
| `distance_km` | float | Distance de la montée (km) |
| `elevation_gain_m` | float | Dénivelé positif (m) |
| `avg_grade_percent` | float | Pente moyenne (%) |
| `pace_s_per_km` | float | Allure médiane (s/km) |
| `vam_m_h` | float | Vitesse ascensionnelle (m/h) |
| `start_idx` | int | Index de début |
| `end_idx` | int | Index de fin |
| `distance_m_end` | float | Distance cumulée à la fin (m) |
| `start_km` | float | Kilomètre de début |
| `end_km` | float | Kilomètre de fin |
| `start_end_km` | string | Plage formatée ("xx.xx → yy.yy") |
| `duration_s` | float | Temps de mouvement (s) |

Les items sont triés par `elevation_gain_m` décroissant. La liste complète est renvoyée (pas de top N).

## Notes

- Le seuil de vitesse pour le masque moving est `MOVING_SPEED_THRESHOLD_M_S = 0.5 m/s` (défini dans `backend/core/constants.py`)
- Depuis la version v1.1.46, une machine d'état avec gap bridging remplace l'ancien seuillage point par point
