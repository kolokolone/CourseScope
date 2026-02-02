# pace_vs_grade (Allure vs pente)

Ce document decrit la logique backend utilisee par l'endpoint `GET /activity/{id}/pace-vs-grade`.

## Objectif

Produire une courbe d'allure (s/km) en fonction de la pente (%), avec:
- des bins fixes pour comparer entre activites
- une definition "moving" (incluant marche) qui exclut les pauses/arrêts
- des agrégats ponderes par le temps (`delta_time_s`)
- un traitement robuste des outliers uniforme sur toutes les pentes

## Donnees d'entree (DataFrame)

Colonnes utilisees (unites):
- `pace_s_per_km` (s/km)
- `delta_time_s` (s)
- `speed_m_s` (m/s) (utilisee pour detecter les pauses)
- `delta_distance_m` (m) et `elevation` (m) (pour calculer la pente si aucune serie n'est fournie)

La pente est en pourcentage (%): `(delta_elev / delta_distance_m) * 100`.

## Definition "moving" (incluant marche)

Le filtrage des pauses utilise `compute_moving_mask` (module `backend/core/real_run_analysis.py`):
- vitesse instantanee lissee (mediane glissante)
- une pause est detectee si la vitesse lissee reste sous le seuil pendant >= 5s
- les points non-moving sont exclus du calcul pace_vs_grade

Note: le seuil de vitesse est `MOVING_SPEED_THRESHOLD_M_S = 0.5 m/s`.

## Serie d'allure (unification endpoint / figures)

L'endpoint et les figures utilisent la meme construction d'allure via `compute_pace_series`:
- base: `pace_s_per_km` ("real_time") ou pace "moving_time" (optionnel)
- lissage: rolling mean centre avec `window = smoothing_points + 1`
- cap: `cap_min_per_km` (min/km) converti en `s/km`

Par defaut (app): `RealRunViewParams()`.

## Binning pente

1) La pente est clippee a `[-20, +20]`.
2) Bins fixes de 0.5% avec bornes incluses:
   - `bins = np.arange(-20, 20.5, 0.5)`
   - `pd.cut(..., include_lowest=True, right=True)`

Cela garantit l'inclusion de `-20` (borne basse) et de `+20` (borne haute).

## Pondération (temps)

Les poids sont `w_i = delta_time_s` (apres filtrage moving).

On calcule:
- `time_s_bin = sum(w)`
- `pace_n_eff` (effectif de poids): `(sum(w)^2) / sum(w^2)`

## Outliers (robuste, par bin)

Objectif: traiter de facon uniforme toutes les pentes.

Approche: winsorisation (clipping) par bin, basee sur des quantiles ponderes:
- si le bin est suffisamment supporte (`time_s_bin >= 30s` et `pace_n_eff >= 8`)
- bornes via IQR:
  - `q25_w`, `q75_w`, `IQR = q75_w - q25_w`
  - `lo = q25_w - 2.0*IQR`, `hi = q75_w + 2.0*IQR`
- fallback MAD si IQR ~ 0 (valeurs quasi constantes)
- sinon, pas de winsorisation

On expose `outlier_clip_frac`: fraction du temps clippe dans le bin.

## Agrégats par bin

Les champs existants sont preserves:
- `pace_med_s_per_km` (utilise pour la courbe)
- `pace_std_s_per_km`
- `pace_n`

Nouveaux champs optionnels:
- `time_s_bin`
- `pace_mean_w_s_per_km`
- `pace_q25_w_s_per_km`, `pace_q50_w_s_per_km`, `pace_q75_w_s_per_km`
- `pace_iqr_w_s_per_km`
- `pace_std_w_s_per_km`
- `pace_n_eff`
- `outlier_clip_frac`

## Qualite des bins (anti-bruit)

Les bins trop peu supportes sont exclus des resultats:
- `time_s_bin >= 20s`
- `pace_n_eff >= 5`

## API

Endpoint: `GET /activity/{id}/pace-vs-grade`

Reponse:
- `bins`: liste d'objets (un par bin retenu)
- `pro_ref`: courbe reference (table embarquee `backend/core/resources/pro_pace_vs_grade.csv`)
