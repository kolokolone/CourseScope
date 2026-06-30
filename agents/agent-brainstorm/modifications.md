# Modifications à implémenter — CourseScope

Date : 2026-06-30 18:00
Source : agents/modifications.txt
Produit par : agents/agent-brainstorm.md
Statut : prêt pour agent-dev

## 1. Résumé exécutif

L'utilisateur demande la correction/amélioration des monolithes frontend identifiés dans `docs/audit_application.md` (Section 5, Tableau « Frontend — composants > 300 lignes »).

**Contexte** : les extractions de fonctions dupliquées frontend (`lib/dateUtils.ts`, `lib/chartUtils.ts`, `lib/paceUtils.ts`) ont déjà été réalisées en v1.1.93. La suppression des composants inutilisés (HeroKpi, MetricTile, SidebarStats, activityStore) aussi. Le découpage des monolithes backend a été fait en v1.1.94.

**Ce qui reste** : les 4 pages frontend monolithes à découper en composants réutilisables, plus l'optimisation `useMemo` du composant `ActivityCharts`.

**Périmètre retenu** : découpage des 4 pages monolithes + optimisation ActivityCharts. Aucune modification backend, aucun changement de contrat API, aucun changement fonctionnel utilisateur.

**Priorisation** :
- **P0** : `app/progress/page.tsx` (~1100 lignes) — page la plus complexe (8 queries, 9 sections de graphes)
- **P0** : `app/goals/page.tsx` (~650 lignes) — composants internes extractibles proprement
- **P1** : `app/activities/[id]/page.tsx` (~785 lignes) — page legacy, la vue beta existe déjà
- **P1** : `app/traces/[id]/page.tsx` (~521 lignes) — le plus petit monolithe
- **P1** : `components/charts/ActivityCharts.tsx` (~430 lignes) — optimisation useMemo + suppression doublons

Au total : **~15 nouveaux composants** extraits, **2 nouveaux fichiers utilitaires**, **0 modification de comportement**.

## 2. Demandes utilisateur extraites

### Demande 1 — Découpage des monolithes frontend

- **Texte source** : « corriger/améliorer les monolithes frontend, comme décrit dans docs\audit_application.md »
- **Interprétation** : L'utilisateur veut appliquer les recommandations de l'audit concernant les 4 pages frontend > 300 lignes, en extrayant les sections en composants réutilisables.
- **Statut** : retenue
- **Justification** : La demande est explicite et s'appuie sur un audit existant. Les extractions déjà faites (v1.1.93) ont prouvé la viabilité de l'approche. Le découpage améliore la maintenabilité et la testabilité sans risque de régression fonctionnelle.

## 3. Diagnostic de l'existant

### 3.1 Fichiers et zones lus

- `docs/audit_application.md` — Section 5 (monolithes frontend), Section 4 (redondances), Section 10 (recommandations)
- `CHANGELOG.md` — v1.1.93 (extraction utilitaires frontend), v1.1.94 (découpage backend)
- `frontend/src/app/progress/page.tsx` — 1089 lignes, 9 sections de graphes, indexation polling
- `frontend/src/app/activities/[id]/page.tsx` — 785 lignes, 6 onglets, KPI builder inline
- `frontend/src/app/goals/page.tsx` — 652 lignes, composants Timeline et GoalsCalendar inline, formulaire inline
- `frontend/src/app/traces/[id]/page.tsx` — 521 lignes, résolution de route, inputs pace/temps
- `frontend/src/components/charts/ActivityCharts.tsx` — 430 lignes, smoothing recalculé à chaque render
- `frontend/src/components/charts/` — 10 composants existants
- `frontend/src/components/features/progress/` — CalendarHeatmap.tsx, TrainingLoadChart.tsx (existants)
- `frontend/src/components/goals/` — GoalMiniCard.tsx, GoalsObjectivesMap.tsx, GoalsObjectivesMapLeaflet.tsx, GoalsTimelineFlow.tsx (existants)
- `frontend/src/components/metrics/` — 11 composants existants (KpiHeader, MetricGrid, etc.)
- `frontend/src/components/activity-beta/` — 17 composants (modèle de référence pour le découpage)
- `frontend/src/lib/chartUtils.ts` — rollingMean, rollingMeanPoints, samplePoints, buildPoints
- `frontend/src/lib/dateUtils.ts` — startOfDay, dateAtStart, formatDateLabel, isoDateUtc, etc.
- `frontend/src/lib/paceUtils.ts` — parseFlexibleSeconds, formatPaceInputFromSeconds, formatTimeInputFromSeconds
- `frontend/src/components/layout/page-metadata.tsx` — metadata des pages
- `docs/style-frontend-ui.md` — guide UI normatif

### 3.2 Constats établis

1. **`app/progress/page.tsx`** contient 9 sections de graphes distinctes, un système d'indexation polling, 8 queries React Query, et ~20 blocs `useMemo` de transformation de données. Les sections sont indépendantes et peuvent être extraites une par une.
2. **`app/goals/page.tsx`** définit 2 composants internes (`Timeline`, `GoalsCalendar`) et un formulaire inline (`goalFormCard`). Ces composants sont déjà bien isolés dans le code mais définis dans le même fichier.
3. **`app/activities/[id]/page.tsx`** (vue legacy) définit `buildActivityDetailSections` (7 sections A-G), `buildKpiItems`, `KPI_HELP` et `DETAIL_HELP`. La logique métier de construction des tiles est mélangée au rendu.
4. **`app/traces/[id]/page.tsx`** a une section d'inputs pace/temps bien délimitée et une barre de titre éditable. Le reste est du rendu de tabs simple.
5. **`ActivityCharts.tsx`** définit `smoothMovingAverage` (doublon partiel de `rollingMeanPoints` dans chartUtils) et `buildSeriesData` (doublon partiel de `buildPoints`). Le smoothing n'est pas memoizé, recalculé à chaque render.
6. Les composants `activity-beta/` servent de modèle : chaque sous-section est un composant dédié avec des props typées, rendu par une page fine (`ActivityBetaPage.tsx` de 11 lignes).
7. Les utilitaires extraits en v1.1.93 (`dateUtils.ts`, `chartUtils.ts`, `paceUtils.ts`) sont correctement importés par les pages.
8. Aucun test unitaire frontend n'existe pour ces pages spécifiques. Les seuls tests frontend sont `metricsFormat.test.ts`, `metricsRegistry.test.ts`, `routes.test.ts`, `network-handling.test.ts`.

### 3.3 Hypothèses

- Le découpage composant par composant ne cassera pas le comportement existant si chaque étape est vérifiée par `npm run build`.
- Les nouveaux composants peuvent être placés dans `components/features/progress/` (pour progress), `components/goals/` (pour goals), `components/metrics/` (pour les tiles d'activité).
- La page `progress/page.tsx` gardera la logique de queries et de transformation de données, mais déléguera le rendu à des sous-composants (pattern "container/presentational").
- `ActivityCharts` peut être corrigé sans changer son interface publique.

### 3.4 Incertitudes

- Impact sur les performances : le découpage en plus de composants peut introduire des re-renders supplémentaires si les props ne sont pas stables. Vérifier avec `React.memo` si nécessaire.
- La page `activities/[id]` est la vue legacy — la vue beta existe. Faut-il investir dans son découpage ou attendre la migration complète vers la vue beta ? L'audit recommande le découpage en « moyen terme ». Je recommande de le faire quand même (P1 plutôt que P0) car la vue legacy est encore la vue par défaut.
- Le fichier `ActivityCharts.tsx` a 430 lignes (pas 506 comme indiqué dans l'audit) — le fichier a peut-être déjà été réduit depuis.

## 4. Spécification fonctionnelle cible

Aucun changement fonctionnel. L'objectif est purement structurel : extraire des composants sans modifier le comportement observable.

**Contrat de non-régression** :
- Toutes les pages affichent exactement les mêmes données qu'avant.
- Les interactions utilisateur (clics, sélections, formulaires) fonctionnent à l'identique.
- Le build `npm run build` passe sans erreur.
- Les quelques tests frontend existants continuent de passer.

**Comportement cible par page après découpage** :

### Progress
- La page principale gère les queries, l'état global (range, filtres), et le polling d'indexation.
- Chaque section de graphe est un composant indépendant recevant ses données en props.
- Les constantes et helpers sont dans des fichiers séparés.

### Goals
- Le formulaire de création/édition est un composant `GoalForm` autonome.
- Le calendrier est un composant `GoalsCalendar` dans `components/goals/`.
- La timeline est un composant `GoalsTimelineCard` (wrapper Card autour de `GoalsTimelineFlow`).
- La table de liste est un composant `GoalListTable`.

### Activities (legacy)
- Les sections de détail (A-G) sont rendues par un composant `ActivityDetailSections`.
- Les insights sont rendus par `ActivityInsights`.
- La barre de titre éditable est dans `ActivityTitleBar`.
- Les helpers de construction de tiles sont déplacés dans `components/metrics/activityDetails.ts`.

### Traces (theoretical)
- Le panneau d'inputs pace/temps est dans `TraceInputPanel`.
- La barre de titre éditable est dans `TraceTitleBar`.

### ActivityCharts
- Le smoothing est wrappé dans `useMemo`.
- `smoothMovingAverage` remplacé par `rollingMeanPoints` (chartUtils).
- `buildSeriesData` remplacé par `buildPoints` (chartUtils).

## 5. Spécification technique proposée

### 5.1 Frontend — Découpage de `app/progress/page.tsx`

#### 5.1.1 Nouveaux fichiers à créer

| Fichier | Contenu | Lignes estimées |
|---|---|---|
| `components/features/progress/constants.ts` | `VOLUME_METRICS`, `HR_AT_PACE_REFS`, `PACE_AT_HR_REFS`, `SERIES_COLORS`, `SESSION_FILTER_OPTIONS`, `TERRAIN_FILTER_OPTIONS` | ~60 |
| `components/features/progress/utils.ts` | `parseBucketStartMs`, `formatBucketLabel`, `finiteNumber`, `quantile`, `paddedDomain` | ~60 |
| `components/features/progress/ProgressVolumeChart.tsx` | Volume chart card (AreaChart) avec sélecteurs intervalle/métrique | ~100 |
| `components/features/progress/ProgressTrimpChart.tsx` | TRIMP chart card (ComposedChart bar+line) | ~70 |
| `components/features/progress/ProgressBestEffortsChart.tsx` | Best efforts chart card (AreaChart) avec sélecteur durée | ~100 |
| `components/features/progress/ProgressEfficiencyCharts.tsx` | Grille 2 colonnes : EF + Decoupling (ComposedChart scatter+line) | ~180 |
| `components/features/progress/ProgressHrPaceCharts.tsx` | Grille 2 colonnes : HR@pace + Pace@HR (ComposedChart multi-lines) | ~200 |
| `components/features/progress/ProgressVo2maxChart.tsx` | VO2max trend chart (3 derniers mois) | ~70 |
| `components/features/progress/ProgressWaterfallCard.tsx` | Waterfall 3D card avec filtres (session, terrain, bin step, limit, endurance) | ~80 |
| `components/features/progress/ProgressIndexationBanner.tsx` | Bannière indexation en cours / erreur | ~50 |

#### 5.1.2 Page résiduelle

La page `app/progress/page.tsx` après extraction contiendra (~300 lignes) :
- L'état global (`range`, `volumeMetric`, `bestDuration`, filtres waterfall)
- Le `useEffect` d'indexation polling
- Les 8 queries React Query
- Les `useMemo` de transformation de données
- L'assemblage des sous-composants

**Props de chaque sous-composant** :

```typescript
// ProgressVolumeChart
type ProgressVolumeChartProps = {
  data: Array<{ bucket_start: string; weekStartMs: number; value: number | null }>;
  isLoading: boolean;
  error: Error | null;
  range: HistoryRange;
  volumeMetric: ProgressSeriesMetric;
  volumeSpec: VolumeMetricSpec;
  currentWeekBucketStart: string;
  onRangeChange: (range: HistoryRange) => void;
  onVolumeMetricChange: (metric: ProgressSeriesMetric) => void;
  indexationRunning: boolean;
};

// ProgressTrimpChart
type ProgressTrimpChartProps = {
  data: Array<{ bucket_start: string; weekStartMs: number; trimp: number | null; acute: number | null; chronic: number | null }>;
  isLoading: boolean;
  error: Error | null;
};

// ProgressBestEffortsChart
type ProgressBestEffortsChartProps = {
  data: Array<{ start_ts_utc: string; value: number; is_pr: boolean; dateMs: number }>;
  isLoading: boolean;
  error: Error | null;
  bestDuration: number;
  bestYAxisDomain: [number, number];
  onDurationChange: (duration: number) => void;
};

// ProgressEfficiencyCharts
type ProgressEfficiencyChartsProps = {
  efData: Array<{ dateMs: number; ef: number; trend: number | null }>;
  decouplingData: Array<{ dateMs: number; dec: number; trend: number | null }>;
  isLoading: boolean;
  error: Error | null;
  efDomain: [number, number];
  decouplingDomain: [number, number];
};

// ProgressHrPaceCharts
type ProgressHrPaceChartsProps = {
  hrAtPaceData: Array<Record<string, number>>;
  hrAtPaceMeta: Array<{ key: string; label: string }>;
  paceAtHrData: Array<Record<string, number>>;
  paceAtHrMeta: Array<{ key: string; label: string }>;
  isLoadingHr: boolean;
  isLoadingPace: boolean;
  errorHr: Error | null;
  errorPace: Error | null;
  hrAtPaceDomain: [number, number];
  paceAtHrDomain: [number, number];
};

// ProgressVo2maxChart
type ProgressVo2maxChartProps = {
  data: Array<{ dateMs: number; vo2max: number }>;
  domain: [number, number];
};

// ProgressWaterfallCard
type ProgressWaterfallCardProps = {
  activities: WaterfallActivity[];
  isLoading: boolean;
  error: Error | null;
  waterfallLimit: 10 | 30 | 60;
  waterfallBinStep: 5 | 10;
  waterfallSessionTag: 'all' | ProgressSessionTag;
  waterfallTerrainTag: 'all' | ProgressTerrainTag;
  waterfallEnduranceOnly: boolean;
  onLimitChange: (limit: 10 | 30 | 60) => void;
  onBinStepChange: (step: 5 | 10) => void;
  onSessionTagChange: (tag: 'all' | ProgressSessionTag) => void;
  onTerrainTagChange: (tag: 'all' | ProgressTerrainTag) => void;
  onEnduranceOnlyChange: (value: boolean) => void;
};

// ProgressIndexationBanner
type ProgressIndexationBannerProps = {
  state: ProgressIndexStatusResponse | null;
};
```

### 5.2 Frontend — Découpage de `app/goals/page.tsx`

#### 5.2.1 Nouveaux fichiers à créer

| Fichier | Contenu | Lignes estimées |
|---|---|---|
| `components/goals/utils.ts` | `addDays`, `addWeeks`, `isoDayKey`, `mondayStartOfWeek`, `goalDaysDeltaFromToday`, `goalCountdownLabel`, `monthWarmth`, `monthBackgroundStyle`, `goalObjectiveLabel`, `compareGoals` | ~100 |
| `components/goals/GoalsCalendar.tsx` | Composant calendrier (extrait du inner component `GoalsCalendar`) | ~120 |
| `components/goals/GoalsTimelineCard.tsx` | Card wrapper autour de `GoalsTimelineFlow` (extrait du inner component `Timeline`) | ~20 |
| `components/goals/GoalForm.tsx` | Formulaire création/édition d'objectif | ~200 |
| `components/goals/GoalListTable.tsx` | Table triable des objectifs | ~100 |

#### 5.2.2 Page résiduelle

La page `app/goals/page.tsx` après extraction contiendra (~150 lignes) :
- Les queries (`useGoalsList`, `useCreateGoal`, etc.)
- L'état du formulaire (`isFormOpen`, `editingGoalId`)
- L'état de tri (`sortKey`, `sortDir`)
- La logique `onSubmit`
- L'assemblage des sous-composants

#### 5.2.3 Props des nouveaux composants

```typescript
// GoalForm
type GoalFormProps = {
  isOpen: boolean;
  editingGoal: GoalItem | null;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (payload: GoalCreateRequest | GoalUpdateRequest) => Promise<void>;
};

// GoalsCalendar
type GoalsCalendarProps = {
  goals: GoalItem[];
};

// GoalsTimelineCard
type GoalsTimelineCardProps = {
  goals: GoalItem[];
  countdownByGoalId: Record<string, string>;
};

// GoalListTable
type GoalListTableProps = {
  goals: GoalItem[];
  isLoading: boolean;
  sortKey: SortKey;
  sortDir: SortDir;
  today: Date;
  countdownByGoalId: Record<string, string>;
  onSort: (key: SortKey) => void;
  onEdit: (goal: GoalItem) => void;
  onDelete: (goalId: string) => Promise<void>;
  isDeleting: boolean;
  onAdd: () => void;
};
```

### 5.3 Frontend — Découpage de `app/activities/[id]/page.tsx`

#### 5.3.1 Nouveaux fichiers à créer

| Fichier | Contenu | Lignes estimées |
|---|---|---|
| `components/metrics/activityDetails.ts` | `KPI_HELP`, `DETAIL_HELP`, `detailHelpText`, `DetailTile`/`DetailSection` types, `hasRenderableValue`, `firstAvailable`, `tile`, `buildActivityDetailSections`, `buildKpiItems`, `formatRaceDate` | ~200 |
| `components/activity/ActivityDetailSections.tsx` | Rendu des 7 sections de détail A-G avec tiles | ~120 |
| `components/activity/ActivityInsights.tsx` | Cartes d'insights (dérive cardio, relief, rythme) | ~80 |
| `components/activity/ActivityTitleBar.tsx` | Barre de titre éditable + bouton vue bêta + ID activité | ~80 |
| `components/activity/ActivityKpiBar.tsx` | Barre de KPIs primaires (pills) + KPIs secondaires (grille) | ~100 |

#### 5.3.2 Page résiduelle

La page `app/activities/[id]/page.tsx` après extraction contiendra (~200 lignes) :
- La query principale (`useRealActivity`, `useRealActivityBins`, `useMapData`)
- L'état des tabs
- La logique de rename
- Le rendu par tab (overview, splits, climbs, charts, map, details)

### 5.4 Frontend — Découpage de `app/traces/[id]/page.tsx`

#### 5.4.1 Nouveaux fichiers à créer

| Fichier | Contenu | Lignes estimées |
|---|---|---|
| `components/traces/TraceInputPanel.tsx` | Panneau mode pace/time + inputs + bouton Appliquer + VMA info | ~120 |
| `components/traces/TraceTitleBar.tsx` | Barre titre éditable + bouton Save/Star + statut trace | ~100 |
| `components/traces/utils.ts` | `computeDefaultPaceFromVma` | ~25 |

#### 5.4.2 Page résiduelle

La page `app/traces/[id]/page.tsx` après extraction contiendra (~120 lignes) :
- La résolution de route (trace → activity)
- Les queries
- L'état des tabs
- Le rendu par tab (overview, charts, map)

### 5.5 Frontend — Optimisation `ActivityCharts.tsx`

#### 5.5.1 Modifications

| Changement | Détail |
|---|---|
| Supprimer `smoothMovingAverage` (l. 44-70) | Remplacer par `rollingMeanPoints` de `lib/chartUtils.ts`. Note : `rollingMeanPoints` est une rolling mean causale (forward-only), tandis que `smoothMovingAverage` est centrée. **Conserver `smoothMovingAverage` dans `chartUtils.ts` comme `rollingMeanCentered` pour ne pas changer le comportement.** |
| Supprimer `buildSeriesData` (l. 32-42) | Remplacer par `buildPoints` de `lib/chartUtils.ts` (interface identique) |
| Wrapper smoothing dans `useMemo` | Les calculs `smoothMovingAverage` pour chaque série HR doivent être wrappés dans `React.useMemo` dépendant des données brutes et de la fenêtre de lissage |

#### 5.5.2 Fichiers impactés

- `components/charts/ActivityCharts.tsx` — suppression doublons + ajout useMemo
- `lib/chartUtils.ts` — ajout optionnel de `rollingMeanCentered` si nécessaire

### 5.6 Documentation

- Mettre à jour `CHANGELOG.md` avec entrée « Refactor: découpage des 4 monolithes frontend »
- Mettre à jour `docs/audit_application.md` §5 : marquer les monolithes frontend ✅

## 6. Plan d'implémentation pour agent-dev

### Étape 1 — P0 : Extraire les constantes et helpers de progress

- **Objectif** : Créer `components/features/progress/constants.ts` et `components/features/progress/utils.ts`
- **Fichiers** :
  - `components/features/progress/constants.ts` (création) — `VOLUME_METRICS`, `HR_AT_PACE_REFS`, `PACE_AT_HR_REFS`, `SERIES_COLORS`, `SESSION_FILTER_OPTIONS`, `TERRAIN_FILTER_OPTIONS`
  - `components/features/progress/utils.ts` (création) — `parseBucketStartMs`, `formatBucketLabel`, `finiteNumber`, `quantile`, `paddedDomain`
  - `app/progress/page.tsx` — remplacer définitions par imports
- **Tests** : `npm run build`
- **Risques** : Aucun — simple déplacement de code

### Étape 2 — P0 : Extraire ProgressIndexationBanner

- **Objectif** : Isoler la bannière d'indexation dans un composant dédié
- **Fichiers** :
  - `components/features/progress/ProgressIndexationBanner.tsx` (création)
  - `app/progress/page.tsx` — remplacer JSX inline par `<ProgressIndexationBanner>`
- **Tests** : `npm run build`
- **Risques** : Aucun — composant purement présentatif

### Étape 3 — P0 : Extraire ProgressVolumeChart

- **Objectif** : Isoler le graphe de volume dans un composant dédié
- **Fichiers** :
  - `components/features/progress/ProgressVolumeChart.tsx` (création)
  - `app/progress/page.tsx` — remplacer JSX inline par `<ProgressVolumeChart>`
- **Tests** : `npm run build`
- **Risques** : Vérifier que le `renderVolumeDot` callback fonctionne correctement après extraction (dépend de `currentWeekBucketStart` dans la closure)

### Étape 4 — P0 : Extraire ProgressTrimpChart

- **Objectif** : Isoler le graphe TRIMP
- **Fichiers** : `components/features/progress/ProgressTrimpChart.tsx` (création), `app/progress/page.tsx`
- **Tests** : `npm run build`

### Étape 5 — P0 : Extraire ProgressBestEffortsChart

- **Objectif** : Isoler le graphe best efforts
- **Fichiers** : `components/features/progress/ProgressBestEffortsChart.tsx` (création), `app/progress/page.tsx`
- **Tests** : `npm run build`
- **Risques** : `bestDot` callback dépend du payload `is_pr` — vérifier après extraction

### Étape 6 — P0 : Extraire ProgressEfficiencyCharts

- **Objectif** : Isoler la grille EF + Decoupling
- **Fichiers** : `components/features/progress/ProgressEfficiencyCharts.tsx` (création), `app/progress/page.tsx`
- **Tests** : `npm run build`

### Étape 7 — P0 : Extraire ProgressHrPaceCharts

- **Objectif** : Isoler la grille HR@pace + Pace@HR
- **Fichiers** : `components/features/progress/ProgressHrPaceCharts.tsx` (création), `app/progress/page.tsx`
- **Tests** : `npm run build`
- **Risques** : Ce composant est le plus complexe (multi-lines, légende dynamique)

### Étape 8 — P0 : Extraire ProgressVo2maxChart

- **Objectif** : Isoler le graphe VO2max
- **Fichiers** : `components/features/progress/ProgressVo2maxChart.tsx` (création), `app/progress/page.tsx`
- **Tests** : `npm run build`

### Étape 9 — P0 : Extraire ProgressWaterfallCard

- **Objectif** : Isoler le waterfall 3D avec ses filtres
- **Fichiers** : `components/features/progress/ProgressWaterfallCard.tsx` (création), `app/progress/page.tsx`
- **Tests** : `npm run build`

### Étape 10 — P0 : Extraire les helpers de goals

- **Objectif** : Créer `components/goals/utils.ts`
- **Fichiers** :
  - `components/goals/utils.ts` (création) — 10 fonctions helper
  - `app/goals/page.tsx` — remplacer définitions par imports
  - `components/goals/GoalsCalendar.tsx` — importer depuis utils.ts au lieu de définitions inline
  - `components/goals/GoalsTimelineCard.tsx` — idem
- **Tests** : `npm run build`

### Étape 11 — P0 : Extraire GoalsCalendar et GoalsTimelineCard

- **Objectif** : Déplacer les inner components vers `components/goals/`
- **Fichiers** :
  - `components/goals/GoalsCalendar.tsx` (création, basé sur le inner component l.125-226)
  - `components/goals/GoalsTimelineCard.tsx` (création, basé sur le inner component l.112-123)
  - `app/goals/page.tsx` — remplacer par imports
- **Tests** : `npm run build`

### Étape 12 — P0 : Extraire GoalForm

- **Objectif** : Extraire le formulaire CRUD dans un composant autonome
- **Fichiers** :
  - `components/goals/GoalForm.tsx` (création)
  - `app/goals/page.tsx` — remplacer JSX inline par `<GoalForm>`
- **Tests** : `npm run build`
- **Risques** : Le formulaire gère à la fois la création et l'édition. Props d'initialisation à bien définir.

### Étape 13 — P0 : Extraire GoalListTable

- **Objectif** : Extraire la table triable dans un composant
- **Fichiers** :
  - `components/goals/GoalListTable.tsx` (création)
  - `app/goals/page.tsx` — remplacer JSX inline par `<GoalListTable>`
- **Tests** : `npm run build`

### Étape 14 — P1 : Extraire les helpers d'activité

- **Objectif** : Créer `components/metrics/activityDetails.ts`
- **Fichiers** :
  - `components/metrics/activityDetails.ts` (création) — `KPI_HELP`, `DETAIL_HELP`, `detailHelpText`, types, `buildActivityDetailSections`, `buildKpiItems`, `formatRaceDate`
  - `app/activities/[id]/page.tsx` — remplacer définitions par imports
- **Tests** : `npm run build`

### Étape 15 — P1 : Extraire ActivityTitleBar et ActivityKpiBar

- **Objectif** : Isoler la barre de titre et la barre de KPIs
- **Fichiers** :
  - `components/activity/ActivityTitleBar.tsx` (création)
  - `components/activity/ActivityKpiBar.tsx` (création)
  - `app/activities/[id]/page.tsx` — remplacer JSX inline
- **Tests** : `npm run build`
- **Risques** : La logique de rename (`handleRenameActivity`, `isEditingTitle`) doit être passée en props

### Étape 16 — P1 : Extraire ActivityDetailSections et ActivityInsights

- **Objectif** : Isoler les sections de détail et les insights
- **Fichiers** :
  - `components/activity/ActivityDetailSections.tsx` (création)
  - `components/activity/ActivityInsights.tsx` (création)
  - `app/activities/[id]/page.tsx` — remplacer JSX inline
- **Tests** : `npm run build`

### Étape 17 — P1 : Extraire les helpers de traces

- **Objectif** : Créer `components/traces/utils.ts`
- **Fichiers** :
  - `components/traces/utils.ts` (création) — `computeDefaultPaceFromVma`
  - `app/traces/[id]/page.tsx` — remplacer par import

### Étape 18 — P1 : Extraire TraceTitleBar et TraceInputPanel

- **Objectif** : Isoler la barre de titre et le panneau d'inputs
- **Fichiers** :
  - `components/traces/TraceTitleBar.tsx` (création)
  - `components/traces/TraceInputPanel.tsx` (création)
  - `app/traces/[id]/page.tsx` — remplacer JSX inline
- **Tests** : `npm run build`

### Étape 19 — P1 : Optimiser ActivityCharts

- **Objectif** : Supprimer les doublons et ajouter useMemo
- **Fichiers** :
  - `components/charts/ActivityCharts.tsx` — wrapper smoothing dans `useMemo`, remplacer `buildSeriesData` par `buildPoints`
  - `lib/chartUtils.ts` — ajouter `rollingMeanCentered` si nécessaire (si `rollingMeanPoints` ne donne pas le même résultat que `smoothMovingAverage`)
- **Vérification** : Comparer visuellement le rendu avant/après ou vérifier que les données produites sont identiques
- **Risques** : `smoothMovingAverage` est centrée, `rollingMeanPoints` est causale. Si le comportement doit être préservé, extraire `smoothMovingAverage` dans `chartUtils.ts` sous le nom `rollingMeanCentered`.

### Étape 20 — Vérification globale

- **Commandes** :
  ```bash
  cd frontend
  npm test
  npm run build
  ```
- **Contrôle manuel** : naviguer sur les 4 pages, vérifier que tous les graphes s'affichent, que les interactions fonctionnent.

### Étape 21 — Documentation

- **Fichiers** : `CHANGELOG.md`, `docs/audit_application.md` §5
- **Action** : Ajouter entrée refactor, marquer ✅ les monolithes frontend

## 7. Tests et vérifications attendus

Frontend :
```bash
cd frontend
npm test
npm run build
```

Vérifications manuelles :
- Page `/progress` : tous les graphes s'affichent, les sélecteurs fonctionnent, la bannière d'indexation apparaît
- Page `/goals` : formulaire création/édition fonctionnel, calendrier affiché, table triable
- Page `/activities/[id]` : KPI header, onglets, sections de détail, charts, map
- Page `/traces/[id]` : résolution de trace, inputs pace/temps, graphes, map
- `ActivityCharts` : les courbes de séries s'affichent correctement (pas de changement visuel)

## 8. Critères d'acceptation

- [ ] `components/features/progress/constants.ts` existe avec toutes les constantes
- [ ] `components/features/progress/utils.ts` existe avec les 5 helpers
- [ ] Les 8 composants progress extraits existent et sont importés par la page
- [ ] `app/progress/page.tsx` < 400 lignes
- [ ] `components/goals/utils.ts` existe avec les 10 helpers
- [ ] `components/goals/GoalsCalendar.tsx` existe
- [ ] `components/goals/GoalsTimelineCard.tsx` existe
- [ ] `components/goals/GoalForm.tsx` existe
- [ ] `components/goals/GoalListTable.tsx` existe
- [ ] `app/goals/page.tsx` < 200 lignes
- [ ] `components/metrics/activityDetails.ts` existe
- [ ] `components/activity/ActivityDetailSections.tsx` existe
- [ ] `components/activity/ActivityInsights.tsx` existe
- [ ] `components/activity/ActivityTitleBar.tsx` existe
- [ ] `app/activities/[id]/page.tsx` < 400 lignes
- [ ] `components/traces/TraceInputPanel.tsx` existe
- [ ] `components/traces/TraceTitleBar.tsx` existe
- [ ] `app/traces/[id]/page.tsx` < 300 lignes
- [ ] `ActivityCharts.tsx` : `smoothMovingAverage` supprimé (ou déplacé dans chartUtils)
- [ ] `ActivityCharts.tsx` : `buildSeriesData` remplacé par `buildPoints`
- [ ] `ActivityCharts.tsx` : smoothing wrappé dans `useMemo`
- [ ] `cd frontend && npm test` passe
- [ ] `cd frontend && npm run build` passe
- [ ] Aucune régression fonctionnelle sur les 4 pages

## 9. Risques et garde-fous

1. **Régressions silencieuses** — le découpage peut introduire des bugs subtils (props manquantes, closures cassées).
   - **Garde-fou** : build après chaque étape, test manuel des pages concernées.

2. **Performances après découpage** — plus de composants = plus de re-renders potentiels.
   - **Garde-fou** : utiliser `React.memo` sur les composants extraits si nécessaire. Les props sont pour la plupart des primitives ou des tableaux stables via `useMemo`.

3. **`smoothMovingAverage` vs `rollingMeanPoints`** — comportement différent (centré vs causal).
   - **Garde-fou** : ne pas remplacer dans ActivityCharts. Déplacer `smoothMovingAverage` dans `chartUtils.ts` sous le nom `rollingMeanCentered` puis l'importer.

4. **`renderVolumeDot` et `bestDot` callbacks** — ces callbacks Recharts capturent `currentWeekBucketStart` via closure.
   - **Garde-fou** : passer ces callbacks en props ou les reconstruire dans le composant enfant avec ses propres dépendances.

5. **Dossiers `components/activity/` et `components/traces/` inexistants** — ces dossiers n'existent pas encore.
   - **Garde-fou** : créer les dossiers avant d'y placer des fichiers. Alternative : placer dans `components/metrics/` (pour activity) et `components/features/traces/` (pour traces).

6. **Vue legacy vs beta** — la page `activities/[id]` est la vue legacy. Ne pas casser la compatibilité avec la vue beta.
   - **Garde-fou** : les fichiers extraits sont nouveaux. La page legacy importe les nouveaux composants. La vue beta n'est pas impactée.

7. **Tests frontend inexistants pour ces pages** — aucun test unitaire ne couvre ces pages.
   - **Garde-fou** : le build et les tests manuels sont la seule vérification. Ajouter des tests n'est pas dans le scope.

## 10. Décisions prises par agent-brainstorm

1. **Périmètre frontend uniquement** — le backend a déjà été traité en v1.1.92 et v1.1.94.
2. **Extraction « container/presentational »** — les pages gardent la logique métier (queries, état, transformations) et délèguent le rendu à des sous-composants.
3. **Pas de nouvelle dépendance** — tous les composants utilisent React, Recharts, et les primitives UI existantes.
4. **Dossiers de destination** : `components/features/progress/` pour progress, `components/goals/` pour goals, `components/activity/` (nouveau) pour la vue legacy activity, `components/traces/` (nouveau) pour traces.
5. **Conservation du comportement exact** — pas de refactor fonctionnel, pas de changement d'UI.
6. **Ordre d'implémentation** : progress d'abord (le plus critique), puis goals, puis activities, puis traces, puis ActivityCharts.
7. **Pas d'extraction des fonctions `hasAnyChartSeries` ni de la logique de sélection de tab** — ces fonctions sont triviales et liées au contexte de la page.
8. **`ActivityCharts`** : ne pas remplacer `smoothMovingAverage` par `rollingMeanPoints` à cause du comportement différent. Déplacer dans `chartUtils.ts` comme `rollingMeanCentered`.

## 11. Points à ne pas faire

- ❌ Ne pas modifier le backend
- ❌ Ne pas modifier les contrats API
- ❌ Ne pas changer le comportement fonctionnel des pages
- ❌ Ne pas supprimer la vue legacy `activities/[id]` (la migration beta n'est pas terminée)
- ❌ Ne pas modifier les composants `activity-beta/` (ils servent de référence)
- ❌ Ne pas modifier `page-metadata.tsx`, `nav.ts`, `AppShell.tsx`
- ❌ Ne pas ajouter de nouvelle dépendance npm
- ❌ Ne pas modifier les tests existants
- ❌ Ne pas créer de documentation supplémentaire (le minimum : CHANGELOG + mise à jour audit)
- ❌ Ne pas committer ni pousser
