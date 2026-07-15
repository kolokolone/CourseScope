# Allure vs pente (`pace-vs-grade`)

> **Type** : Référence technique · **Endpoint** : `GET /activity/{id}/pace-vs-grade`
> **Dernière mise à jour** : v1.2.13

## Objectif

Décrire l'algorithme de binning allure/pente utilisé par le backend pour produire la courbe d'allure en fonction de la pente, avec agrégats pondérés par le temps et traitement robuste des outliers.

## Périmètre

Ce document couvre :
- La construction de la série d'allure
- Le binning de pente (bins fixes de 0.5%)
- La pondération temporelle et les agrégats
- Le traitement des outliers (winsorisation par IQR)
- Le contrat API

Ne couvre pas : l'affichage frontend du graphique Allure vs Pente.

## Données d'entrée (DataFrame)

Colonnes utilisées (unités) :
- `pace_s_per_km` (s/km)
- `delta_time_s` (s)
- `speed_m_s` (m/s) — pour détecter les pauses
- `delta_distance_m` (m), `elevation` (m) — pour calculer la pente

La pente est en pourcentage : `(delta_elev / delta_distance_m) × 100`.

## Définition "moving" (incluant marche)

Le filtrage des pauses utilise `compute_moving_mask` (`backend/core/real_run_analysis.py`) :
- Vitesse instantanée lissée (médiane glissante)
- Pause détectée si vitesse lissée < seuil pendant ≥ 5 s
- Points non-moving exclus du calcul

Seuil : `MOVING_SPEED_THRESHOLD_M_S = 0.5 m/s` (cf. `backend/core/constants.py`).

## Série d'allure

L'endpoint et les figures utilisent `compute_pace_series` :
- Base : `pace_s_per_km` (real_time) ou pace moving_time (optionnel)
- Lissage : rolling mean centré, `window = smoothing_points + 1`
- Cap : `cap_min_per_km` (min/km) converti en `s/km`

## Binning pente

1. Pente clippée à `[-20, +20]`
2. Bins fixes de 0.5% avec bornes incluses :
   - `bins = np.arange(-20, 20.5, 0.5)`
   - `pd.cut(..., include_lowest=True, right=True)`

## Pondération (temps)

Poids : `w_i = delta_time_s` (après filtrage moving).

Métriques de support par bin :
- `time_s_bin = sum(w)` — temps total dans le bin
- `pace_n_eff = (sum(w))² / sum(w²)` — effectif pondéré

## Outliers (winsorisation par bin)

La winsorisation est appliquée si le bin est suffisamment supporté :
- `time_s_bin >= 30 s` et `pace_n_eff >= 8`
- Bornes via IQR pondéré : `lo = q25_w - 2.0 × IQR`, `hi = q75_w + 2.0 × IQR`
- Fallback MAD si IQR ≈ 0

On expose `outlier_clip_frac` : fraction du temps clippé dans le bin.

## Agrégats par bin

| Champ | Description |
|---|---|
| `pace_med_s_per_km` | Médiane pondérée (courbe principale) |
| `pace_std_s_per_km` | Écart-type non pondéré (après winsorisation) |
| `pace_n` | Nombre d'échantillons |
| `time_s_bin` | Temps total dans le bin (s) |
| `pace_mean_w_s_per_km` | Moyenne pondérée |
| `pace_q25_w_s_per_km` | P25 pondéré |
| `pace_q50_w_s_per_km` | P50 pondéré |
| `pace_q75_w_s_per_km` | P75 pondéré |
| `pace_iqr_w_s_per_km` | IQR pondéré |
| `pace_std_w_s_per_km` | Écart-type pondéré |
| `pace_n_eff` | Effectif pondéré |
| `outlier_clip_frac` | Fraction de temps clippé |

## Qualité des bins (anti-bruit)

Bins exclus si :
- `time_s_bin < 20 s`
- `pace_n_eff < 5`

## API

**Endpoint** : `GET /activity/{id}/pace-vs-grade`

**Réponse** :
- `bins` : liste d'objets (un par bin retenu)
- `pro_ref` : courbe de référence pro (table `backend/core/resources/pro_pace_vs_grade.csv`)
