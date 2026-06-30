# Modifications à implémenter — CourseScope

Date : 2026-07-01 11:00
Source : agents/modifications.txt
Produit par : agents/agent-brainstorm.md
Statut : prêt pour agent-dev

## 1. Résumé exécutif

L'utilisateur demande d'incorporer les nouveaux KPI identifiés dans `docs/audit_application.md` section 9 (« Opportunités de nouveaux KPI »). L'audit a identifié 7 opportunités réparties en deux catégories : KPI déjà calculés mais non affichés, et KPI facilement calculables à partir des données existantes.

Après analyse du codebase, le bilan est le suivant :

- **Monotony / Strain** : déjà implémenté et affiché dans `TrainingLoadChart.tsx`. Aucun travail nécessaire.
- **Session taxonomy** : backend + endpoint + hook existent. Aucun composant UI ne les affiche. **Travail : frontend uniquement.**
- **Terrain tags** : même situation que session taxonomy (même endpoint).
- **Activity tagging (manual)** : endpoint `POST /progress/tags` existe. Aucune UI de tagging manuel. **Travail : frontend uniquement.**
- **Intensity distribution** : aucune infrastructure n'existe. **Travail : backend + frontend.**
- **Long run dose** : tag `long_run` auto-assigné par l'indexeur. Compté dans session taxonomy mais pas de visualisation dédiée. **Travail : frontend principalement, backend mineur si série temporelle.**
- **VAM trend** : VAM calculé par montée, stocké dans `ProgressActivityClimb`, mais jamais agrégé ni visualisé en tendance. **Travail : backend + frontend.**

**Priorisation** :
- **P1** : Session taxonomy UI + Intensity distribution — plus fort impact utilisateur, données immédiatement utiles
- **P2** : Long run dose + VAM trend — enrichissement du dashboard
- **P3** : Activity tagging UI — fonctionnalité de confort

## 2. Demandes utilisateur extraites

### Demande 1 — Incorporer les nouveaux KPI de l'audit

- **Texte source** : « incorporer les nouveaux KPI, comme décrit dans docs\audit_application.md dans la section 9. Opportunités de nouveaux KPI »
- **Interprétation** : L'utilisateur veut que tous les KPI listés dans la section 9 de l'audit soient rendus visibles et exploitables dans l'interface, en priorité sur la page Progression.
- **Statut** : retenue
- **Justification** : La demande est explicite, les données sont déjà disponibles pour la plupart des KPI, et l'architecture existante (hooks React Query, composants de progression, service backend ProgressService) fournit un cadre cohérent pour l'ajout.

## 3. Diagnostic de l'existant

### 3.1 Fichiers et zones lus

- `agents/modifications.txt`
- `AGENTS.md`
- `README.md`
- `docs/audit_application.md` — Section 9 (KPI), Section 5 (monolithes), Section 8 (endpoints inutilisés)
- `docs/metrics_catalog.md` — Catalogue complet des métriques API
- `docs/style-frontend-ui.md` — Guide UI normatif
- `docs/documentation_update_runbook.md` — Procédure de mise à jour docs
- `backend/api/routes/progress.py` — 559 lignes, 15+ endpoints, dont training-load, session-taxonomy, tags
- `backend/api/schemas.py` — 291 lignes, schémas Pydantic
- `backend/services/progress_service.py` — 462 lignes : `compute_training_load`, `compute_session_taxonomy`, `build_activity_list`, `merge_tag`, `compute_calendar`, `annotate_prs`
- `backend/progress/indexation_runner.py` — 777 lignes, logique d'indexation avec auto-tagging session/terrain
- `backend/progress/indexer.py` — indexation activity + climbs + daily aggregates
- `backend/db/models.py` — `ProgressActivityIndex` (pas de colonne VAM), `ProgressActivityClimb` (colonne `vam_m_h`), `ProgressDailyAggregate` (pas de VAM)
- `frontend/src/app/progress/page.tsx` — 477 lignes, 10 sections de graphes
- `frontend/src/components/features/progress/TrainingLoadChart.tsx` — 219 lignes, ACWR + monotony + strain
- `frontend/src/hooks/useProgress.ts` — hooks React Query dont `useTrainingLoad()`, `useProgressSessionTaxonomy()` (inutilisé)
- `frontend/src/lib/api.ts` — 542 lignes, client API complet
- `frontend/src/types/api.ts` — types TypeScript complets, `TrainingLoadResponse`, `ProgressSessionTaxonomyResponse`
- `frontend/src/lib/metricsRegistry.ts` — registre de métriques, VAM présent en per-activity uniquement
- `frontend/src/components/features/progress/` — composants existants : CalendarHeatmap, TrainingLoadChart, ProgressVolumeChart, ProgressTrimpChart, ProgressBestEffortsChart, ProgressEfficiencyCharts, ProgressHrPaceCharts, ProgressVo2maxChart, ProgressWaterfallCard

### 3.2 Constats établis

1. **Monotony et Strain sont déjà affichés** dans `TrainingLoadChart.tsx` sous forme de KPI cards avec valeurs actuelles. La colonne vertébrale ACWR est également présente. Aucun travail nécessaire.
2. **L'endpoint `GET /progress/session-taxonomy` est complet** : il retourne `session_counts[]`, `terrain_counts[]`, `race_markers`, `total_tagged`. Le hook `useProgressSessionTaxonomy()` existe dans `useProgress.ts` mais n'est jamais appelé depuis `page.tsx`.
3. **Les tags `long_run` sont auto-assignés** par l'indexeur (`indexer.py:188`) quand `distance >= 18km` OU `moving_time >= 5400s`. Ces activités sont comptabilisées dans session-taxonomy.
4. **Aucune infrastructure d'intensity distribution n'existe** : pas de méthode dans `ProgressService`, pas d'endpoint, pas de hook, pas de composant. Les zones HR/pace/power sont calculées par activité dans `core/metrics.py` (`compute_garmin_like_stats`) mais jamais agrégées par période.
5. **VAM est stocké par montée** dans `ProgressActivityClimb` (colonne `vam_m_h`) mais n'est pas agrégé au niveau activité (`ProgressActivityIndex` n'a pas de colonne VAM) ni au niveau quotidien (`ProgressDailyAggregate` non plus). L'endpoint `/progress/series` ne liste pas VAM dans ses `allowed_metrics`.
6. **L'endpoint `POST /progress/tags` existe** pour le tagging manuel, mais aucune UI ne permet de modifier les tags d'une activité depuis la page progression ou la liste d'activités.
7. **La page progression** (`page.tsx`) rend 10 composants dans un `div.space-y-4`. Les composants sont tous auto-portants (fetch leurs propres données via hooks). Le pattern d'ajout est bien établi.

### 3.3 Hypothèses

- Les tags automatiques (session/terrain) couvrent la majorité des activités réelles. Le tagging manuel viendrait en complément pour corriger ou annoter.
- L'utilisateur consulte principalement la page Progression pour le suivi longitudinal. Les nouveaux KPI doivent donc s'intégrer dans cette page.
- La distribution d'intensité la plus utile est par zone de fréquence cardiaque (car la FC est plus souvent disponible que la puissance).

### 3.4 Incertitudes

- **Performance de l'intensity distribution** : agréger les zones HR par période nécessite soit de lire les données d'activité une par une (lent si beaucoup d'activités), soit de pré-calculer et stocker dans l'index (modification du schéma DB). À trancher dans la spec.
- **VAM trend** : faut-il agréger le VAM max par activité (meilleure performance de grimpe) ou le VAM moyen ? L'audit ne précise pas. Proposition : VAM max par activité (le plus parlant pour un coureur).
- **Page overload** : la page progression a déjà 10 sections. Ajouter 3-4 nouvelles sections risque de la rendre trop longue. Solutions possibles : onglets, sections repliables, ou page dédiée.

## 4. Spécification fonctionnelle cible

### 4.1 Session Taxonomy — Répartition des types de séances

**Comportement attendu** : Une nouvelle section sur la page Progression affiche la répartition des séances par type (easy, tempo, interval, long_run) et par terrain (flat, rolling, hilly), avec le nombre de courses (race_markers).

**États** :
- **Loading** : skeleton card avec placeholder
- **Empty** : message « Aucune activité taguée sur cette période »
- **Error** : message d'erreur avec bouton retry
- **Normal** : bar chart horizontal ou donut chart pour les sessions + petit tableau pour les terrains

**Données affichées** :
- Nombre de séances par tag (barres horizontales, triées par count décroissant)
- Pourcentage par tag
- Total comptabilisé
- Compteur de race markers
- Filtrage par plage de dates (utiliser le `range` selector existant de la page)

**Règles d'arrondi** : counts en entiers, pourcentages arrondis à 1 décimale.

### 4.2 Intensity Distribution — Distribution du temps par zone

**Comportement attendu** : Une nouvelle section affiche la distribution du temps passé dans chaque zone de fréquence cardiaque (Z1-Z5) agrégée par semaine.

**États** :
- **Loading** : skeleton card
- **Empty** : message « Aucune donnée de fréquence cardiaque disponible »
- **Error** : message d'erreur
- **Normal** : stacked bar chart par semaine ou stacked area chart

**Données affichées** :
- Pour chaque semaine : temps (en minutes ou %) passé en Z1, Z2, Z3, Z4, Z5
- Légende avec les plages de FC correspondantes (basées sur FC max effective)
- Total indiqué

**Règles** :
- Activités sans HR exclues silencieusement
- Zones calculées avec FC max effective (celle des settings)
- Temps en minutes, arrondi à l'entier

### 4.3 Long Run Dose — Dose de sorties longues

**Comportement attendu** : Une section dédiée affiche l'évolution de la distance et du temps des sorties longues (tag `long_run`) par semaine.

**États** :
- **Loading** : skeleton card
- **Empty** : message « Aucune sortie longue détectée sur cette période »
- **Error** : message d'erreur
- **Normal** : bar chart distance par semaine + line chart temps par semaine (ou combo chart)

**Données affichées** :
- Distance totale en sortie longue par semaine (km)
- Temps total en sortie longue par semaine (heures)
- Compteur du nombre de sorties longues sur la période
- Optionnel : distance de la plus longue sortie de la semaine

**Règles** :
- Une « sortie longue » est définie par le tag `long_run` (distance ≥ 18km ou temps ≥ 90 min)
- Distance en km, arrondie à 1 décimale
- Temps en heures, arrondi à 1 décimale

### 4.4 VAM Trend — Tendance de vitesse ascensionnelle

**Comportement attendu** : Une section affiche l'évolution du meilleur VAM par activité au fil du temps.

**États** :
- **Loading** : skeleton card
- **Empty** : message « Aucune montée détectée sur cette période »
- **Error** : message d'erreur
- **Normal** : scatter plot (points par activité) + trend line (moyenne glissante)

**Données affichées** :
- VAM max (m/h) par activité contenant au moins une montée
- Moyenne glissante sur 4-6 semaines
- Unité : m/h

**Règles** :
- Activités sans montée exclues silencieusement
- VAM max = valeur la plus élevée parmi les montées de l'activité
- Arrondi à l'entier

## 5. Spécification technique proposée

### 5.1 Frontend

#### Pages à modifier
- `frontend/src/app/progress/page.tsx` — ajouter 4 nouveaux composants dans le layout existant `div.space-y-4`

#### Composants à créer

1. **`frontend/src/components/features/progress/ProgressSessionTaxonomy.tsx`** (nouveau)
   - Récupère les données via `useProgressSessionTaxonomy()`
   - Affiche bar chart horizontal pour session_counts
   - Affiche petit tableau pour terrain_counts
   - Props : `from`, `to` (dates), `activityType` (optionnel)
   - Utilise Recharts `BarChart` / `Bar` (horizontal)
   - Suit le pattern visuel de `TrainingLoadChart.tsx` : Card wrapper, titre, contenu

2. **`frontend/src/components/features/progress/ProgressIntensityDistribution.tsx`** (nouveau)
   - Récupère les données via un nouveau hook `useProgressIntensityDistribution()`
   - Affiche stacked bar chart par semaine (Z1-Z5)
   - Props : `from`, `to` (dates), `activityType` (optionnel)
   - Utilise Recharts `BarChart` avec `stackId` pour les zones
   - Couleurs : dégradé de vert à rouge pour Z1→Z5

3. **`frontend/src/components/features/progress/ProgressLongRunDose.tsx`** (nouveau)
   - Récupère les données via un nouveau hook `useProgressLongRunDose()`
   - Affiche combo chart (barres = distance, ligne = temps)
   - Props : `from`, `to` (dates)
   - Utilise Recharts `ComposedChart`

4. **`frontend/src/components/features/progress/ProgressVamTrend.tsx`** (nouveau)
   - Récupère les données via un nouveau hook `useProgressVamTrend()`
   - Affiche scatter plot + trend line
   - Props : `from`, `to` (dates)
   - Utilise Recharts `ScatterChart` + `Line` pour la tendance

#### Hooks à créer

1. **`useProgressIntensityDistribution(from, to, activityType?)`** — dans `useProgress.ts`
   - Appelle un nouvel endpoint `GET /progress/intensity-distribution`
   - Retourne `{ data, isLoading, error }` avec le type approprié

2. **`useProgressLongRunDose(from, to)`** — dans `useProgress.ts`
   - Appelle un nouvel endpoint `GET /progress/long-run-dose` (ou réutilise `/progress/series` filtré)

3. **`useProgressVamTrend(from, to)`** — dans `useProgress.ts`
   - Appelle un nouvel endpoint `GET /progress/vam-trend`

#### Types à ajouter (dans `types/api.ts`)

```typescript
// Intensity Distribution
interface IntensityDistributionPoint {
  bucket_start: string;       // "YYYY-MM-DD"
  z1_time_min: number;        // minutes
  z2_time_min: number;
  z3_time_min: number;
  z4_time_min: number;
  z5_time_min: number;
  total_time_min: number;
}
interface IntensityDistributionResponse {
  points: IntensityDistributionPoint[];
  zone_thresholds_bpm: { z1: number; z2: number; z3: number; z4: number; z5: number };
}

// Long Run Dose
interface LongRunDosePoint {
  bucket_start: string;
  distance_km: number;
  moving_time_h: number;
  activity_count: number;
  max_distance_km: number;
}

// VAM Trend
interface VamTrendPoint {
  activity_id: string;
  start_ts_utc: string;
  vam_max_m_h: number;
}
```

#### Contraintes UI à respecter
- Suivre `docs/style-frontend-ui.md` : pas de header local, utiliser `Card`, tokens Tailwind existants
- Cohérence avec les composants existants : même rythme `space-y-4`, même style de Card
- Responsive : `grid-cols-1 md:grid-cols-2` pour les paires de charts si pertinent
- Couleurs de zones : utiliser un schéma lisible et accessible (contraste suffisant)
- États loading/error/empty pour chaque composant

### 5.2 Backend

#### Nouveaux endpoints

1. **`GET /progress/intensity-distribution`** (nouveau)
   - Routeur : `progress.py`
   - Query params : `from`, `to` (dates), `activity_type` (optionnel)
   - Logique : pour chaque activité entre `from` et `to` avec HR, agréger le temps par zone (Z1-Z5) par semaine
   - Schéma de zone : `<60%`, `60-70%`, `70-80%`, `80-90%`, `>90%` de FC max effective
   - Utiliser FC max effective depuis settings (ou fallback 220-age)
   - Méthode : `ProgressService.compute_intensity_distribution(rows, hr_max)`

2. **`GET /progress/long-run-dose`** (nouveau)
   - Routeur : `progress.py`
   - Query params : `from`, `to` (dates)
   - Logique : filtrer les activités avec `session_tag == 'long_run'`, agréger distance et temps par semaine
   - Méthode : `ProgressService.compute_long_run_dose(rows)`
   - Alternative si léger : réutiliser `/progress/activities?session_tag=long_run` et agréger côté frontend. **Recommandation : endpoint dédié pour la propreté.**

3. **`GET /progress/vam-trend`** (nouveau)
   - Routeur : `progress.py`
   - Query params : `from`, `to` (dates)
   - Logique : pour chaque activité, lire `ProgressActivityClimb` et prendre le `MAX(vam_m_h)`, retourner les points triés par date
   - Méthode : nouvelle query dans `ProgressRepository` + `ProgressService.compute_vam_trend(rows)`
   - Ajouter `vam_max_m_h` aux `allowed_metrics` de `/progress/series` si on veut aussi le graphique existant (optionnel P2)

#### Méthodes à ajouter dans `ProgressService`

```python
# backend/services/progress_service.py

@staticmethod
def compute_intensity_distribution(rows, hr_max: float) -> dict:
    """Agrège le temps par zone HR par semaine."""
    # rows = liste d'objets avec .start_ts_utc, .z1_time_s, .z2_time_s... ou lit depuis les bins
    
@staticmethod
def compute_long_run_dose(rows) -> dict:
    """Agrège distance/temps des long runs par semaine."""

@staticmethod
def compute_vam_trend(rows) -> dict:
    """Formate les points VAM max par activité."""
```

#### Approche données pour l'intensity distribution

Deux options :
- **Option A (recommandée)** : Ajouter les colonnes `z1_time_s` à `z5_time_s` dans `ProgressActivityIndex` lors de l'indexation (comme le TRIMP). Stocker le temps passé dans chaque zone HR par activité. L'agrégation par semaine devient un simple SUM groupé.
- **Option B** : Calculer à la volée en lisant les données parquet de chaque activité. Plus lent mais sans modification du schéma DB.

**Recommandation : Option A**, car :
- Cohérent avec l'approche existante (TRIMP, EF, etc. sont déjà dans l'index)
- Performant pour les requêtes dashboard
- La modification du schéma DB est minime (ajout de 5 colonnes float)
- Nécessite une réindexation slow après migration

#### Modifications DB (Option A)

- **`ProgressActivityIndex`** (`backend/db/models.py` vers ligne 175) : ajouter 5 colonnes :
  ```python
  z1_time_s = Column(Float)
  z2_time_s = Column(Float)
  z3_time_s = Column(Float)
  z4_time_s = Column(Float)
  z5_time_s = Column(Float)
  ```
- **`indexer.py`** : dans `index_activity()`, après le calcul des zones HR, stocker le temps par zone dans l'index
- **`recompute_daily_aggregates()`** (`indexer.py:669`) : ajouter les sommes par zone


#### Modifications DB (VAM)

- **Option simple** : Nouvel endpoint qui lit `ProgressActivityClimb` directement (pas de modification DB nécessaire)
- **Repo** : Ajouter une méthode `list_climb_max_vam(session, from_ts, to_ts)` dans `ProgressRepository`

### 5.3 Données et métriques

| Métrique | Unité | Source | Fallback si absent |
|---|---|---|---|
| Session counts | nombre entier | `ProgressActivityTag.session_tag` | "unknown" |
| Terrain counts | nombre entier | `ProgressActivityTag.terrain_tag` | "unknown" |
| Zone HR time | minutes | Zones calculées depuis HR + FC max | Série vide (activité sans HR exclue) |
| Long run distance | km | `ProgressActivityIndex.distance_m / 1000` filtré `long_run` | 0 |
| Long run time | heures | `ProgressActivityIndex.moving_time_s / 3600` filtré `long_run` | 0 |
| VAM max | m/h | `MAX(ProgressActivityClimb.vam_m_h)` par activité | null (activité sans montée exclue) |

### 5.4 Documentation

- **`docs/metrics_catalog.md`** : ajouter les 3 nouveaux endpoints (intensity-distribution, long-run-dose, vam-trend) avec leurs métriques, types et unités
- **`CHANGELOG.md`** : ajouter entrée v1.1.96 mentionnant les nouveaux KPI

## 6. Plan d'implémentation pour agent-dev

### Étape 1 — Session Taxonomy UI (frontend only)

- **Objectif** : Afficher la répartition des types de séances sur la page Progression
- **Fichiers probables** :
  - `frontend/src/components/features/progress/ProgressSessionTaxonomy.tsx` (créer)
  - `frontend/src/app/progress/page.tsx` (modifier : import + rendu)
- **Détails d'implémentation** :
  1. Créer `ProgressSessionTaxonomy.tsx` : Card avec bar chart horizontal (Recharts `BarChart` layout="vertical")
  2. Utiliser `useProgressSessionTaxonomy(from, to)` (hook existant)
  3. Afficher barres pour `session_counts` (easy, tempo, interval, long_run, unknown)
  4. Sous-section compacte pour `terrain_counts` et `race_markers`
  5. Ajouter dans `page.tsx` après `TrainingLoadChart` (ou après `ProgressTrimpChart`)
- **Tests à prévoir** : test unitaire du composant (mock du hook)
- **Risques** : faibles — hook déjà testé, composant purement visuel

### Étape 2 — Intensity Distribution (backend + frontend)

- **Objectif** : Afficher l'évolution du temps passé par zone HR par semaine
- **Fichiers probables** :
  - `backend/db/models.py` (modifier : ajout colonnes z1-z5 sur ProgressActivityIndex)
  - `backend/progress/indexer.py` (modifier : stocker temps par zone dans l'index)
  - `backend/services/progress_service.py` (modifier : ajouter `compute_intensity_distribution`)
  - `backend/api/routes/progress.py` (modifier : ajouter endpoint)
  - `frontend/src/types/api.ts` (modifier : ajouter types)
  - `frontend/src/lib/api.ts` (modifier : ajouter méthode `intensityDistribution()`)
  - `frontend/src/hooks/useProgress.ts` (modifier : ajouter hook)
  - `frontend/src/components/features/progress/ProgressIntensityDistribution.tsx` (créer)
  - `frontend/src/app/progress/page.tsx` (modifier)
- **Détails d'implémentation** :
  1. Ajouter `z1_time_s` à `z5_time_s` (Float, nullable) dans `ProgressActivityIndex`
  2. Dans `indexer.py:index_activity()` : après appel à `compute_garmin_like_stats()` qui retourne les zones HR, calculer le temps par zone et le stocker
  3. Dans `ProgressService` : `compute_intensity_distribution(rows)` agrégeant par semaine
  4. Endpoint `GET /progress/intensity-distribution` : query params `from`, `to`, `activity_type`, appelle le service
  5. Frontend : hook → composant stacked bar chart → ajout au `page.tsx`
- **Tests à prévoir** : test unitaire du service, test du endpoint, test composant frontend
- **Risques** :
  - Modification du schéma DB → nécessite réindexation slow. **Garde-fou** : les colonnes sont nullable, l'app est rétrocompatible sans réindexation immédiate.
  - Le calcul des zones HR dépend de `hr_max` dans settings → **Garde-fou** : utiliser `hr_max_effective_bpm` si disponible, sinon fallback 220-age.

### Étape 3 — Long Run Dose (backend mineur + frontend)

- **Objectif** : Afficher la progression des sorties longues
- **Fichiers probables** :
  - `backend/services/progress_service.py` (modifier)
  - `backend/api/routes/progress.py` (modifier)
  - `frontend/src/types/api.ts` (modifier)
  - `frontend/src/lib/api.ts` (modifier)
  - `frontend/src/hooks/useProgress.ts` (modifier)
  - `frontend/src/components/features/progress/ProgressLongRunDose.tsx` (créer)
  - `frontend/src/app/progress/page.tsx` (modifier)
- **Détails d'implémentation** :
  1. Backend : endpoint `GET /progress/long-run-dose` filtre `session_tag == 'long_run'` et agrège distance/temps par semaine
  2. Frontend : hook → composant combo chart → ajout au `page.tsx`
- **Tests à prévoir** : test service, test composant
- **Risques** : faibles — données déjà taguées, pas de modification DB

### Étape 4 — VAM Trend (backend + frontend)

- **Objectif** : Afficher la tendance de VAM max par activité
- **Fichiers probables** :
  - `backend/db/progress_repository.py` (modifier : ajouter query climbs)
  - `backend/services/progress_service.py` (modifier)
  - `backend/api/routes/progress.py` (modifier)
  - `frontend/src/types/api.ts` (modifier)
  - `frontend/src/lib/api.ts` (modifier)
  - `frontend/src/hooks/useProgress.ts` (modifier)
  - `frontend/src/components/features/progress/ProgressVamTrend.tsx` (créer)
  - `frontend/src/app/progress/page.tsx` (modifier)
- **Détails d'implémentation** :
  1. `ProgressRepository.list_climb_max_vam(session, from_ts, to_ts)` : `SELECT activity_id, start_ts_utc, MAX(vam_m_h) FROM progress_activity_climbs JOIN ... GROUP BY activity_id`
  2. `ProgressService.compute_vam_trend(rows)` : formate en `[{activity_id, start_ts_utc, vam_max_m_h}]`
  3. Endpoint `GET /progress/vam-trend` avec `from`/`to`
  4. Frontend : hook → scatter plot + trend line → ajout au `page.tsx`
- **Tests à prévoir** : test repository, test service, test composant
- **Risques** :
  - Performances si beaucoup de climbs → **Garde-fou** : `GROUP BY` SQL natif, pas de boucle Python

### Étape 5 — Mise à jour documentation

- **Objectif** : Ajouter les nouveaux endpoints au catalogue de métriques
- **Fichiers probables** : `docs/metrics_catalog.md`, `CHANGELOG.md`
- **Détails** : suivre `docs/documentation_update_runbook.md`

## 7. Tests et vérifications attendus

### Backend

```bash
python -m compileall backend
python -m pytest tests/unit/ -q
python -m pytest tests/pytest/ -q
```

### Frontend

```bash
cd frontend
npm test
npm run build
```

### Vérifications manuelles
- [ ] Page Progression : les 4 nouvelles sections s'affichent sans erreur
- [ ] Session Taxonomy : les compteurs correspondent aux tags dans la DB
- [ ] Intensity Distribution : les zones sont correctement réparties (vérifier avec une activité connue)
- [ ] Long Run Dose : les long runs sont correctement filtrés
- [ ] VAM Trend : les points correspondent aux VAM des montées
- [ ] Responsive mobile : pas de débordement horizontal
- [ ] États vides : message approprié quand pas de données
- [ ] Pas de régression sur les sections existantes

## 8. Critères d'acceptation

1. **Session Taxonomy** : la section affiche un bar chart avec les 5 types de session, les compteurs sont corrects
2. **Intensity Distribution** : le stacked bar chart montre l'évolution hebdomadaire du temps par zone HR
3. **Long Run Dose** : le combo chart affiche distance et temps des long runs par semaine
4. **VAM Trend** : le scatter plot montre les points VAM par activité avec une trend line lissée
5. Tous les nouveaux endpoints sont documentés dans `metrics_catalog.md`
6. `npm run build` passe sans erreur
7. `python -m pytest -q` passe sans régression
8. La page Progression reste navigable et performante (< 2s de chargement initial)
9. Aucun anti-pattern UI : pas de header local, pas de container racine dupliqué, utilisation des tokens Tailwind

## 9. Risques et garde-fous

- **Risque 1 — Surcharge de la page Progression** : 4 nouvelles sections ajoutées à une page qui en a déjà 10. **Garde-fou** : les composants sont légers (pas de calculs lourds côté frontend). Si la page devient trop longue, proposer dans une itération future de grouper les sections en onglets.
- **Risque 2 — Réindexation nécessaire pour intensity distribution** : l'ajout de colonnes z1-z5 dans `ProgressActivityIndex` nécessite une réindexation slow pour les activités existantes. **Garde-fou** : les colonnes sont `nullable`. Les activités non réindexées auront `NULL` → le frontend les exclut du calcul. Pas de données erronées.
- **Risque 3 — Performance des queries climbs pour VAM trend** : si beaucoup d'activités avec montées, la query pourrait être lente. **Garde-fou** : la query utilise un `GROUP BY` SQL natif avec index sur `activity_id`. Limiter le range par défaut à 6 mois.
- **Risque 4 — FC max non configurée** : l'intensity distribution nécessite la FC max pour calculer les zones. **Garde-fou** : si `hr_max_effective_bpm` est null, utiliser `hr_max_detected_bpm`, puis fallback 220-30=190. Si toujours pas de FC max, l'endpoint retourne une liste vide avec un message.

## 10. Décisions prises par agent-brainstorm

1. **Monotony/Strain ignorés** : déjà implémentés et affichés. Inutile de les refaire.
2. **Intensity distribution = zones HR uniquement** : les zones pace et power sont optionnelles (données pas toujours disponibles). La FC est la métrique la plus universelle pour le running. Ajouter pace/power plus tard si demandé.
3. **Option A pour l'intensity distribution** : ajouter colonnes dans `ProgressActivityIndex` plutôt que calcul à la volée. Plus performant et cohérent avec l'architecture d'indexation existante.
4. **VAM max par activité** plutôt que VAM moyen : le VAM max (meilleure performance de grimpe) est plus parlant pour suivre la progression en montée.
5. **Pas d'onglets pour l'instant** : ajouter les sections dans le flux existant de la page Progression. Réévaluer la nécessité d'onglets après usage.
6. **Long run dose = endpoint dédié** : plutôt que de réutiliser `/progress/activities?session_tag=long_run` et agréger côté frontend, un endpoint dédié est plus propre et plus performant.
7. **Tagging manuel UI repoussé en P3** : complexité UI plus élevée (modale ou formulaire inline, sélection d'activité, etc.). Non prioritaire pour cette itération.

## 11. Points à ne pas faire

- **Ne pas modifier `compute_training_load`** : la méthode est complète et fonctionnelle
- **Ne pas refactorer `page.tsx` au-delà de l'ajout des composants** : le découpage a déjà été fait
- **Ne pas toucher aux endpoints existants** : tous les nouveaux endpoints sont des ajouts, pas des modifications
- **Ne pas modifier les contrats API existants** : rétrocompatibilité obligatoire
- **Ne pas créer de nouvelle page** : tout s'intègre dans la page Progression existante
- **Ne pas ajouter de dépendance npm ou pip**
- **Ne pas modifier `docs/style-frontend-ui.md`** sauf si une décision UI le justifie
- **Ne pas modifier `TrainingLoadChart.tsx`** : monotony/strain y sont déjà
- **Ne pas supprimer les endpoints inutilisés (`/progress/verify`, etc.)** : cf. audit section 8, décision de les garder
