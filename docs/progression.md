# Progression (tendances multi-activites)

Objectif: ajouter une page qui permet de voir, en un coup d'oeil, l'evolution des performances et de la charge en course a pied au fil du temps (comparaison de toutes les courses), sous forme de graphiques longitudinales.

Contraintes
- Ne pas changer le format source: `data/activities/<uuid>/df.parquet` + `meta.json` restent la source de verite.
- Supporter beaucoup d'activites (>= 1 000, potentiellement 10 000) sans scanner tout le filesystem a chaque page.
- Rester local pour l'instant (mono-utilisateur), mais garder une trajectoire possible vers un service en ligne (non prioritaire).
- Garder l'implementation efficace et simple (pas d'architecture cloud en v1).

## Nom de la page

Nom UI (FR) recommande: `Progression`
- Sous-titre: `Tendances multi-activites`

Chemin (URL) recommande (coherent avec `/activities`): `/progress`.
Raison: court, memorizable, et compatible avec une future extension (velo, trail, etc.).

## Ce qui existe deja (etat actuel)

Backend
- Stockage activite: `backend/storage/activity_store.py`
  - Dossier par activite: `data/activities/<uuid>/`
  - Fichiers: `original.*`, `df.parquet`, `meta.json`
- DB SQLite deja en place (optionnelle via env, par defaut `data/coursescope.sqlite`): `backend/db/session.py`
- Un index DB existe deja pour dedupe + sync Garmin: `backend/db/models.py`, `backend/db/repository.py`
- Listing multi-activites actuel (lent a grande echelle): `GET /activities` scanne le disque (pas la DB).

Frontend
- Next.js App Router: `frontend/src/app/*`
- Recharts + React Query: `frontend/package.json`, `frontend/src/lib/api.ts`, `frontend/src/hooks/useActivity.ts`
- Page historique actuelle avec un premier graphe longitudinal (km/semaine) calcule cote frontend depuis `/activities`:
  - `frontend/src/app/activities/page.tsx`

Conclusion: le besoin "progression" depasse `/activities` car on veut des metriques derivees (efficacite, decoupling, best-efforts, etc.) et des requetes rapides.

## Definition backend (senior)

Une implementation "senior backend" pour une page de tendances:
- Evite le scan filesystem par requete.
- Maintient un index analytique incremental (upsert) et versionne les formules.
- Expose des endpoints agreges (bucket day/week/month) et des endpoints chart-friendly (scatter, series).
- Gere la qualite des donnees (timezone, valeurs manquantes, sport type) et la compatibilite (migrations/versions).

## Organisation des donnees: formats et filesystem

### Recommandation (simple + scalable): SQLite comme index analytique

Pourquoi:
- Incrementation atomique (transactions), indexes, requetes rapides.
- Deja present dans CourseScope.
- Pas besoin de recompiler/regenerer un gros fichier global.

Source de verite conservee:
- `data/activities/<uuid>/df.parquet`
- `data/activities/<uuid>/meta.json`

Index analytique (nouveau):
- Reutiliser `data/coursescope.sqlite` (meme DB) en ajoutant des tables "progress".

### Alternative: fichier global par mois (Parquet) (non recommande en v1)

Schema possible:
- `data/analytics/rollups/year=2026/month=02/rollups.parquet`

Avantages:
- Lecture columnar efficace.

Inconvenients:
- Updates incrementales delicats (append/compaction, corruption partielle).
- Plus de complexite operationnelle pour une app locale.
(ne pas utiliser cette alternative)

### Decision (v1 -> v2): SQLite est-il encore le bon choix ?

Objectif (ta note): systeme "puissant et efficace" des la v1, en anticipant une v2 avec beaucoup de donnees longitudinales (potentiellement par utilisateur).

Reponse courte (backend senior):
- Oui, SQLite est une tres bonne option pour v1 ET v2 si l'app reste locale/mono-utilisateur et que la page ne requete que des scalaires (pas des series brutes point-par-point pour chaque activite).
- Si un jour ca devient un service en ligne multi-utilisateur (concurrence, sessions, quotas): l'architecture "index analytique" reste valable, mais le moteur passe typiquement a Postgres (ou equivalent), avec une cle `user_id` partout.

Recommandation concrete:
- v1/v2 local: garder SQLite + tables analytics.
- Option "isolation progression" (si tu veux decoupler les evolutions et garder un fichier dense dedie):
  - Soit: meme fichier `data/coursescope.sqlite` mais tables prefixees (ex: `progress_*`). (choix prioritaire)
  - Soit: fichier separe `data/progression.sqlite` (dedie aux tendances) + backfill. (ne pas faire)

Role des petits fichiers par activite:
- Oui, un fichier par activite (ex: `rollup.json`) peut aider au remplissage/backfill du SQLite et au debug.
- Non, ce n'est pas une bonne "source de requete" pour la page (scanner 1 000 JSON = latence). (seulement à faire s'il y a un réel avantage)

## Conception: index analytique (SQLite)

### Principe

1) A l'ingestion (upload manuel ou sync Garmin), on calcule un petit "resume" par activite.
2) On upsert ce resume dans des tables SQL indexees.
3) Les endpoints de la page Progression lisent UNIQUEMENT ce resume (pas le df complet).

Pourquoi c'est important:
- Le df complet (`df.parquet`) est lourd: IO + parsing + pandas.
- Les dashboards demandent des requetes repetitives et filtrables; un index analytique evite de "recalculer toute l'histoire".

### Fingerprint + versioning (pour incremental et evolutions de formules)

Pour eviter la staleness:
- `fingerprint`: derive de `meta.json` + (mtime/size de `df.parquet`) ou hash stable.
- `metrics_version`: entier bump quand une formule change.
- La reindexation peut etre selective: "toutes les lignes dont metrics_version < current".

Bon pattern (operable):
- `fingerprint_source`: change si une activite change (meta, parquet).
- `fingerprint_formula`: change si la formule change (ex: `metrics_version`).
- Tu peux ainsi reindexer sans ambiguites.

### Tables proposees

Table 1: `activity_index` (1 ligne par activite)
- Champs typiques (typed columns, pas JSON):
  - Identite: `activity_id`, `activity_type`, `start_ts_utc`, `local_date`, `tz`
  - Source/freshness: `fingerprint`, `metrics_version`, `indexed_at_ts`
  - Resume: `distance_m`, `moving_time_s`, `elapsed_time_s`, `elevation_gain_m`
  - Performance: `avg_pace_s_per_km`, `best_pace_s_per_km` (ou p10), `pace_threshold_s_per_km` (si dispo)
  - Cardio: `avg_hr_bpm`, `max_hr_bpm`
  - Load: `trimp`, `training_load_method` (si dispo)
  - Durabilite: `cardiac_drift_pct`, `decoupling_pct` (definition explicite)
  - Qualite: `has_hr`, `has_power`, `has_cadence`, `data_points`

Notes de schema (pour rester stable):
- Stocker des unites explicites dans les noms (ex: `_s_per_km`, `_bpm`, `_m`).
- Ajouter des colonnes sans casser (toutes optionnelles sauf identite/freshness).
- Garder un champ "type de run" (route/trail) si tu veux filtrer les comparaisons.

Table 2: `best_effort_points` (table longue pour courbes)
- Pour stocker les meilleurs efforts par duree standard (ex: 1, 3, 5, 12, 20, 30, 60 min)
- Colonnes:
  - `activity_id`, `start_ts_utc`
  - `effort_kind` (ex: `pace_s_per_km`, `power_w`)
  - `duration_s`
  - `value`

Option (phase 2): `pace_hr_bins`
- Si tu veux vraiment "bpm moyen par allure" de maniere robuste:
  - Pour chaque activite, calculer une petite table de bins `pace_bin_s_per_km -> hr_median_bpm`.
  - Stockage compact: JSON compresse ou table SQL (activity_id, pace_bin, hr_median, time_s).
  - Ensuite, la page peut interpoler `HR @ pace = 5:00/km` ou `pace @ 140 bpm`.

Definition (robuste) suggeree pour `pace_hr_bins`:
- Bins pace en s/km (ex: pas de 5s ou 10s), sur points moving uniquement.
- Pour chaque bin:
  - `time_s_bin` (poids)
  - `hr_mean_w_bpm` ou `hr_q50_w_bpm` (statistique ponderee par `delta_time_s`)
- Exclure les bins avec trop peu de temps (ex: < 60s cumule) pour eviter le bruit.

### Pourquoi typed columns (senior rationale)

- Les dashboards font des queries repetitives sur quelques colonnes (date + valeur + filtres).
- JSON est flexible mais plus lent et moins debuggable pour requetes agregees.
- Les valeurs "pro" (rolling medians, PR, etc.) se font mieux sur colonnes typées + indexes.

## Calcul des metriques (sources)

Priorite v1: reutiliser au maximum ce qui est deja calcule.

Sources existantes exploitables:
- `meta.json`: started_at, created_at, sidebar stats, file_hash.
- `core.metrics.compute_garmin_like_stats`: contient deja:
  - HR summary, zones, training_load (TRIMP), pacing drift (cardiac drift, stability, etc.).
- `core.real_run_analysis`: best efforts, splits, derived series, etc.

Regle de conception (important pour longitudinal):
- Si une metrique depend du "contexte" (terrain, meteo, type de seance), elle doit etre:
  - soit normalisee (ex: grade-adjusted pace, GAP),
  - soit filtree (ex: easy runs uniquement),
  - soit presentee comme scatter (avec covariables) plutot qu'une serie "naive".

Definition example "bpm moyen par allure" (interpretation utilisable):
- Metric UI: `Efficacite aerobique (EF)`
  - Definition: `speed_m_s / avg_hr_bpm` (ou `pace_s_per_km * avg_hr_bpm` selon convention)
  - Lecture: a effort cardio similaire, aller plus vite = progression.
  - Chart: EF vs date (scatter) + rolling median.

Si tu veux strictement "HR a une allure fixe":
- Necessite bins pace->HR (phase 2) car sinon le contexte (terrain, fatigue) biaise fortement.

Alternative equivalente (souvent plus stable):
- "Allure @ HR" (pace a FC fixe) sur des segments easy, avec filtre pente (|grade| < x%).

## Endpoints API proposes (backend)

Objectif: reponses petites, pretes a tracer, filtrables.

1) Activites indexees (liste brute pour scatter)
- `GET /progress/activities?from=...&to=...&type=real`
- Retour: tableau de points (une ligne = une activite) avec champs demandes.

2) Serie agreggee par bucket (day/week/month)
- `GET /progress/series?metric=trimp&group_by=week&agg=sum&from=...&to=...`
- Retour: `[ { bucket_start: 'YYYY-MM-DD', value: number } ]`

3) Scatter generique
- `GET /progress/scatter?x=avg_pace_s_per_km&y=avg_hr_bpm&color=decoupling_pct&from=...&to=...`

4) Progression best-efforts
- `GET /progress/best-efforts?kind=pace_s_per_km&duration_s=1200&from=...&to=...`
- Retour: timeline + flags `is_pr` (running min).

5) Intensity distribution (si disponible)
- `GET /progress/intensity?model=3zone&group_by=week`
- Retour: stacked series Z1/Z2/Z3.

Endpoints complementaires (utile pro, phase 1 ou 2)
6) "Quality flags" (pour filtrer les points)
- `GET /progress/quality?from=...&to=...`
- Retour: par activite, presence capteurs, volume de donnees (data_points), et tags (si introduits).

Note sur le prefix:
- Le backend supporte deja routes avec et sans `/api`.
- Le frontend en dev passe par `/api/*` (rewrite Next.js).

## Frontend: ajout de page et de graphiques

### Ajout de page

Fichier propose:
- `frontend/src/app/progress/page.tsx`

Navigation:
- Lien depuis l'accueil (`frontend/src/app/page.tsx`) et depuis `/activities`.

Data fetching:
- Nouveaux wrappers dans `frontend/src/lib/api.ts` (ex: `progressApi.*`).
- Hooks via React Query (style `useActivityList`).

Charts:
- Recharts (deja utilise), en suivant les patterns de `frontend/src/app/activities/page.tsx`.

### Graphiques recommandes (benefiques a un coureur pro)

Volume / charge
1) Volume hebdo (km, temps, D+)
- Type: stacked toggles + bar/area + rolling average.
- Raison: periodisation, risque de pic de charge.
- réutiliser le meme visuel que celui deja présent sur une autre page +++

2) TRIMP (ou charge cardio) par semaine + acute/chronic
- Type: bars + 2 lignes (7j / 42j) + ratio ACWR.
- Raison: piloter la progression sans surcharger.

3) Intensite (3 zones) par semaine
- Type: stacked bars Z1/Z2/Z3.
- Raison: verifier polarisation vs "trop de seuil".

Performance
4) Best effort progression (durations standard)
- Type: line chart (min is better pour pace) + marquage PR.
- Raison: detecter progression sans course officielle.

5) Critical speed estimate (option phase 2)
- Type: time series + confidence band.
- Raison: proxy "seuil" robuste.

Efficacite / durabilite
6) Efficacite aerobique (EF) vs date
- Type: scatter + rolling median, couleur par temperature (phase 2) ou D+.
- Raison: detecter progression a intensite facile.

7) Aerobic decoupling / cardiac drift (sur longues sorties)
- Type: points par sortie longue + guideline (ex: < 5%).
- Raison: durabilite, resistance a la fatigue/heat.

8) Pace vs HR (scatter) sur toutes activites
- Type: scatter x=pace, y=avg_hr, couleur=date ou charge.
- Raison: visualiser "meme cardio, plus vite".

Qualite de course
9) Pacing stability (CV/IQR) vs date
- Type: line/scatter.
- Raison: regularite, endurance.

10) Long run dose (plus longue sortie / semaine)
- Type: weekly points.
- Raison: marathon readiness.

Autres metriques longitudinales pertinentes (liste supplementaire)

Metriques de charge / risque
- Monotony (charge monotone): mean(weekly load) / std(weekly load) sur 7 jours (a definir precisement).
- Strain: load_week * monotony (utile pour surveiller semaines "dangereuses").
- Density: minutes "seuil et plus" / volume total (intensity density).

Metriques de performance (sans course officielle)
- PR timeline par distance cible (1k/5k/10k/HM/42k) a partir des best-efforts.
- Efficiency @ easy pace (EF) sur fenetre pace (ex: 5:30-6:00/km) + filtre pente.
- GAP trend: allure ajustee pente moyenne vs date (si GAP serie existe deja).

Metriques de durabilite
- Long-run drift (delta pace ou delta HR sur 1ere vs 2e moitie) sur sorties longues uniquement.
- Split stability sur sorties tempo: CV pace ou IQR ratio sur segments selectionnes.

Metriques "terrain" (si tu veux progresser en trail/montee)
- VAM sur montees detectees (median VAM des N plus grosses montees).
- Climb pace (pace median en montee sur segments detectes) vs date.

Metriques capteurs (si FIT complet)
- Cadence @ easy pace (cadence mediane quand pace dans une fenetre).
- Power @ pace (si puissance dispo): watts moyens a allure fixe.
- Running dynamics (si dispo): trend sur GCT, vertical ratio, etc. (attention au bruit/compatibilite).

### Interaction UX (pro)

- Filtres: type d'activite (real/theoretical), plage de dates, exclure trail/hilly (si tag), selection "sortie longue".
- Smoothing: rolling median (robuste) et rolling mean.
- Marqueurs: races/test days, blessures (manual tags en phase 2).

## Strategie de calcul et de mise a jour (incremental)

Point d'insertion recommande (unique pour upload + Garmin):
- `LocalTempStorage.store` dans `backend/storage/activity_store.py` (juste apres ecriture df/meta)

Deux options d'execution:
1) Synchronous (simple):
- Calcul rollup + upsert DB pendant le store.
- OK si computation courte.

2) Async post-response (plus fluide UI et préferer si plus rapide):
- Retourner l'activite au client.
- Lancer une tache de fond (thread) qui indexe.
- Exposer un endpoint "index status".

Critere de choix (senior):
- Si l'indexation ajoute > 300-500ms au upload/sync, passer en async.
- Garder une garantie de coherences:
  - l'activite existe meme si l'index est en retard.
  - la page Progression affiche "indexation en cours" plutot que des graphes incomplets sans explication. +++

Backfill/reindex:
- Script CLI (ex: `scripts/reindex_progress.py`) qui parcourt `data/activities/*` et upsert.
- Utile si on change `metrics_version`.

## Performance et scalabilite

Objectif latence page:
- < 200ms pour requetes de series (hors cold start).

Principes:
- Une activite = quelques dizaines de scalaires. Stocker dans SQLite et indexer sur `start_ts`.
- Ne pas charger `df.parquet` pour des requetes de dashboard.
- Limiter les points renvoyes (bucket week/month/year par defaut, downsample cote backend si besoin).
- Garder le calcul en backend, le frontend s'occupe seulement de montrer les données.

SLA de scalabilite (indicatif)
- 1 000 activites: requetes series/scatter instantanees.
- 10 000 activites: OK si on renvoie surtout des buckets (week/month) + scatter downsample.
- Au-dela: necessite regles plus strictes (pagination, pre-aggregations, caching).

## Tests (plan)

Backend
- Unit tests: compute rollup sur fixtures FIT/GPX.
- Repo tests: queries `group_by=week`, PR progression.
- API tests: endpoints /progress.* (status codes, shape JSON).

Frontend
- Tests unitaires de composants charts (a minima "renders with empty") comme existant.
- E2E manuel: verifier que l'UI reste fluide avec 1 000 activites (simulate).

## References (metriques longitudinales)

Des sources utiles pour la selection des metriques (non marketing):
- Intensite / distribution: https://pubmed.ncbi.nlm.nih.gov/20861519/
- Critical power/speed framing: https://pmc.ncbi.nlm.nih.gov/articles/PMC5371646/
- Running economy: https://pmc.ncbi.nlm.nih.gov/articles/PMC4555089/
- Cardiovascular drift: https://journals.lww.com/acsm-essr/fulltext/2001/04000/cardiovascular_drift_during_prolonged_exercise_.9.aspx
- Session-RPE load: https://journals.lww.com/nsca-jscr/abstract/2001/02000/a_new_approach_to_monitoring_exercise_training.19.aspx
- TRIMP / fitness-fatigue: https://pubmed.ncbi.nlm.nih.gov/6778623/
- ACWR framing (avec prudence): https://pmc.ncbi.nlm.nih.gov/articles/PMC4789704/

## Phasage recommande

Phase 1 (valeur rapide)
- Index SQLite + endpoints series/scatter basiques.
- Graphiques: volume hebdo, TRIMP, best efforts progression, EF, decoupling.

Livrables Phase 1 (definition "done")
- Backend: schema SQL + indexer incremental + 3 endpoints minimum (activities/series/best-efforts).
- Frontend: page `/progress` + 4 graphes (volume hebdo, charge, best efforts, EF/decoupling).
- Tests: au moins 1 fixture multi-activites et 1 test de regression sur buckets.

Phase 2 (precision "bpm par allure")
- Stocker bins pace->HR et exposer "HR@pace" / "pace@HR".

Livrables Phase 2
- Definition stable des bins + filtres (moving, pente, temps min par bin).
- Graphes: HR@pace (2-3 allures de reference) + pace@HR (2-3 HR).

Phase 3 (qualite pro)
- Tagger sessions (interval, tempo, easy, long run) + race markers.
- Ajouter ce graphique en suivant le prompt que j'ai eu avec chatgpt (tu devras faire attention à bien adapter au code que j'utilise, au language que j'utilise, à la performance, à l'UI) :
"
Explication rapide du graphique (c’est quoi, à quoi ça sert)

Le “Pace–HR Waterfall 3D” est une visualisation longitudinale qui empile, pour une série d’activités, la relation Allure ↔ Fréquence cardiaque. Chaque activité devient une courbe “BPM en fonction de l’allure”, et ces courbes sont rangées dans le temps (ancien → récent) pour voir d’un coup d’œil si, à allure équivalente, la FC baisse (progression), monte (fatigue/conditions), ou si la relation se déforme (dérive cardio, changement de profil d’effort). Le binning (par pas d’allure) transforme les données brutes en courbes comparables, évitant l’effet “spaghetti plot”.

Rendu 3D recommandé (React) — “Pace–HR Waterfall”
Pourquoi (pas) Plotly/Matplotlib

Pour un graphe 3D dense en production web, il faut un rendu GPU (WebGL) stable et contrôlable (perf, lisibilité, interaction). Deux options réalistes : three.js / react-three-fiber (R3F) (flexible, rendu “propre”, hautement custom) ou deck.gl (excellent pour très gros volumes, moins adapté si tu veux une esthétique de lignes 3D très maîtrisée). Reco : R3F.

Stack frontend

three

@react-three/fiber

@react-three/drei (OrbitControls, Text, helpers)

(optionnel) three-stdlib / three/examples si besoin de primitives avancées (ex: lignes épaisses via Line2)

Composant et contrat de données
Composant

<PaceHr3DChart activities={...} binStep={...} />

Format attendu

Le frontend doit recevoir des courbes déjà nettoyées + binées (le rendu ne doit pas faire d’ETL lourd). Chaque activité : { date, points: [{ paceBinSecPerKm, hrBpm }, ...] } avec un nombre de points borné (ex. 50–160).

Mapping des axes (référence)

X = Date (index 0..N-1) × xSpacing (ancien → récent)

Y = Allure (paceBinSecPerKm) avec affichage mm:ss/km et axe inversé (plus rapide = visuellement plus “haut”)

Z = BPM (hrBpm)
Caméra/scene réglées pour : X = profondeur temporelle, Y = vertical lisible, Z = BPM bien séparé.

Style visuel (temps → couleur/opacité)
Gradient temporel

Ancien → gris (#8c8c8c) ; récent → rouge (#ff0000). Pour l’activité i (0 ancien, N-1 récent) : w = i/(N-1) ; color = lerp(grey, red, w) ; opacity = 0.18 + 0.82*w.

Épaisseur / emphase

Courbe la plus récente : plus épaisse. Les anciennes : plus fines + plus transparentes. ⚠️ LineBasicMaterial n’assure pas l’épaisseur sur la majorité des GPUs WebGL : si tu veux une épaisseur fiable, utilise Line2 (ou une approche “tube/mesh”).

Géométrie (lignes 3D)

1 activité = 1 polyline 3D : points (x, y, z) où x = dateIndex * xSpacing, y = paceBinSecPerKm (ou -paceBinSecPerKm si tu préfères inverser dans le repère), z = hrBpm. Deux niveaux : Simple (polylines standard) vs Produit (Line2 / mesh) pour un rendu premium.

Échelles, normalisation, lisibilité

Conserver les unités brutes (sec/km, bpm) est OK, mais prévoir yScale / zScale si la scène devient écrasée. L’inversion “faster is higher” doit être cohérente : soit inverser l’axe Y dans la scène, soit garder Y positif et inverser les ticks/labels (souvent plus propre). Garder une amplitude raisonnable (limites min/max) pour éviter que des outliers dominent.

Axes, ticks, labels (rendu “propre”)

X (dates) : ~6 ticks (tous les ceil(N/6)), format YYYY-MM-DD.

Y (allure) : 6–8 ticks, affichage mm:ss/km (conversion sec → mm:ss).

Z (bpm) : 4–6 ticks (ex 120/140/160/180 selon plage réelle).
Rendu via drei/Text (3D) ou overlay DOM (souvent plus net et plus “UI-friendly”).

Caméra & contrôles

OrbitControls : rotation/zoom/pan. Vue initiale calibrée pour : profondeur temporelle évidente (X), verticalité lisible (Y), séparation BPM (Z). Option : limiter l’angle vertical pour éviter les vues “à l’envers” et conserver une lecture stable.

Interaction minimale (utile en prod)

Hover d’une courbe : augmenter opacité/épaisseur + tooltip (date, plage allure, plage bpm). Option avancée : hover d’un point (picking) et tooltip exact (date, allure, bpm).

Performance (contraintes concrètes)

Avec binning, ordre de grandeur : 30 activités × 50–150 points = 1500–4500 vertices → OK. Bonnes pratiques : mémoriser géométries/matériaux (useMemo), recalcul uniquement si activities/binStep changent, pas d’animations inutiles (éviter un render loop coûteux).

Paramètres UI à exposer (Progression)

limit : 10 / 30 / 60 activités ; binStep : 5s / 10s (sec/km) ; filtres : route/trail, type de séance (si tags) ; option “endurance only” pour éviter que les intervalles polluent la lecture.

Acceptance criteria (testables)

N activités → N courbes empilées sur X, ordre ancien → récent. Axe Y affiché en mm:ss/km, lecture “plus rapide = plus haut” via inversion cohérente. Couleur/opacité encode le temps : ancien ~ gris transparent, récent ~ rouge opaque. Binning 10s produit moins de points/activité et des courbes visuellement plus lisses. Rendu initial fluide (<300ms hors fetch) sur machine standard avec 30 activités binées.
"

Livrables Phase 3
- Taxonomie seances + rules de detection (ou tags manuels).
- Comparaisons "like-for-like": memes types de seances, memes conditions (pente/temperature si dispo).

## Work protocol (pour l'implementation)

Note (ta retouche, formalisee):
- Le developpement doit suivre `agents/agent-dev.md`.
- Mission: examiner/implementer la nouvelle page decrite dans `docs/progression.md`.