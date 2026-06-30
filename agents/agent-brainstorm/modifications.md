# Modifications à implémenter — CourseScope

Date : 2026-06-30 14:10
Source : docs/modifications.txt
Produit par : agents/agent-brainstorm.md
Statut : prêt pour agent-dev

## 1. Résumé exécutif

Trois axes de modifications demandés :
1. **Page `/progress`** : ajout de deux nouveaux composants (Calendrier heatmap et Charge d'entraînement ACWR/Monotonie/Strain) avec leurs endpoints backend respectifs.
2. **Application globale** : réduction de la largeur de la sidebar de 15% et ajout du numéro de version à côté du titre "CourseScope".
3. **Page d'accueil `/`** : correction du positionnement du point sur la jauge VO2 max (actuellement toujours au maximum).

Les demandes 1 et 3 sont techniques et bien cadrées par les docs existants (`calendrier-implementation.md`, `charge-entrainement-implementation.md`). La demande 2 est structurelle et impacte le shell global.

Priorisation :
- **P1** — Calendrier + Charge d'entraînement (back + front), car fonctionnalités directement utiles
- **P1** — Correction jauge VO2 max, car bug visible
- **P2** — Sidebar -15% + version, car amélioration UX sans blocage

## 2. Demandes utilisateur extraites

### Demande 1 — Calendrier heatmap dans /progress

- **Texte source** : `un Calendrier (docs/calendrier-implementation.md) qui sera positionné sous le graphique "Volume hebdo"`
- **Interprétation** : Ajouter le composant CalendarHeatmap décrit dans la doc d'implémentation, avec son endpoint backend `/progress/calendar`, et l'insérer dans la page `/progress` juste après la carte "Volume hebdo" (avant "Charge (TRIMP) par semaine").
- **Statut** : retenue
- **Justification** : Spécification complète et validée dans le doc source. Toutes les dépendances backend (`ProgressRepository.list_activity_rows`, table `progress_activity_index`) existent déjà.

### Demande 2 — Charge d'entraînement dans /progress

- **Texte source** : `un graphique de charge (docs/charge-entrainement-implementation.md) qui sera positionné sous le graphique "Charge (TRIMP) par semaine"`
- **Interprétation** : Ajouter le composant TrainingLoadChart avec son endpoint `/progress/training-load`, inséré juste après la carte "Charge (TRIMP) par semaine" (avant "Best effort").
- **Statut** : retenue
- **Justification** : Spécification complète. Dépendances backend (`ProgressRepository.list_series_rows(metric="trimp")`, colonne `trimp` existante) satisfaites.

### Demande 3 — Sidebar -15% + version

- **Texte source** : `je veux réduire la barre latérale de 15% de largeur, ajouter une petite mention de la version à la suite du titre "CourseScope" et avec la meme taille de police que le texte "Analyse d'activites de course"`
- **Interprétation** : 
  - Largeur sidebar desktop actuelle : `260px` → cible : `221px` (260 × 0.85). Arrondi à `220px` pour la propreté CSS (écart négligeable de ~0.4%).
  - Version affichée à côté du titre "CourseScope" dans le bloc branding de la sidebar, avec la même typographie que le sous-titre (`text-xs text-muted-foreground`).
- **Statut** : retenue
- **Justification** : Demandes directes. La sidebar est déjà un composant isolé (Sidebar.tsx), le changement de largeur est localisé dans AppShell.tsx. La version est déjà exposée par `GET /` (utilisé par `metaApi.root()` dans `HeaderActions.tsx`).

### Demande 4 — Correction jauge VO2 max page d'accueil

- **Texte source** : `revoir le mecanisme du petit point qui doit se positionner correctement en fonction du chiffre de la vo2max, en ce moment il est toujours positionné au maximum de la jauge`
- **Interprétation** : Bug de calcul trigonométrique : le code actuel utilise `Math.cos` pour x et `Math.sin` pour y avec un angle en convention CSS (0° = haut, sens horaire), alors que les fonctions trigonométriques JS utilisent la convention mathématique (0° = droite, sens anti-horaire). Il faut adapter la conversion.
- **Statut** : retenue
- **Justification** : Bug confirmé par analyse du code (voir section 3.2). Correction isolée sur 2 lignes dans `page.tsx`.

## 3. Diagnostic de l'existant

### 3.1 Fichiers et zones lus

- `docs/modifications.txt`
- `docs/calendrier-implementation.md`
- `docs/charge-entrainement-implementation.md`
- `docs/style-frontend-ui.md`
- `README.md`
- `CHANGELOG.md`
- `frontend/src/app/page.tsx` (page d'accueil + jauge VO2 max)
- `frontend/src/app/progress/page.tsx` (page /progress, 1200 lignes)
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/nav.ts`
- `frontend/src/components/layout/page-metadata.tsx`
- `frontend/src/components/layout/HeaderActions.tsx`
- `frontend/src/types/api.ts` (488 lignes)
- `frontend/src/lib/api.ts` (529 lignes)
- `frontend/src/hooks/useProgress.ts` (162 lignes)
- `frontend/package.json`
- `backend/api/routes/progress.py` (844 lignes)
- `backend/db/progress_repository.py` (296 lignes)

### 3.2 Constats établis

**Calendrier :**
- ❌ L'endpoint `GET /progress/calendar` n'existe pas.
- ❌ Les types `CalendarDay`, `CalendarResponse` n'existent pas dans `types/api.ts`.
- ❌ La méthode `progressApi.calendar()` n'existe pas dans `lib/api.ts`.
- ❌ Le hook `useCalendar()` n'existe pas dans `hooks/useProgress.ts`.
- ❌ Le composant `CalendarHeatmap.tsx` n'existe pas.
- ✅ `ProgressRepository.list_activity_rows()` existe (ligne 178 de `progress_repository.py`), accepte `from_ts_utc`, `to_ts_utc`, `activity_type`, `limit`.
- ✅ La table `progress_activity_index` contient `start_ts_utc`, `distance_m`, `moving_time_s`.
- ✅ `_parse_ts_utc()` existe dans `progress.py` (ligne 160).

**Charge d'entraînement :**
- ❌ L'endpoint `GET /progress/training-load` n'existe pas.
- ❌ Les types `TrainingLoadPoint`, `TrainingLoadResponse` n'existent pas.
- ❌ La méthode `progressApi.trainingLoad()` n'existe pas.
- ❌ Le hook `useTrainingLoad()` n'existe pas.
- ❌ Le composant `TrainingLoadChart.tsx` n'existe pas.
- ✅ `ProgressRepository.list_series_rows()` existe (ligne 199), accepte `metric`, `from_ts_utc`, `to_ts_utc`, `activity_type`.
- ✅ La colonne `trimp` existe dans `progress_activity_index`.
- ✅ L'indexeur remplit déjà `trimp` lors de l'indexation.

**Sidebar :**
- Largeur actuelle définie dans `AppShell.tsx` ligne 49 : `md:grid-cols-[260px_minmax(0,1fr)]`.
- Le bloc branding est dans `Sidebar.tsx` lignes 17-19 : titre "CourseScope" (`text-lg font-semibold`) + sous-titre (`text-xs text-muted-foreground`).
- ✅ La version applicative est disponible via `GET /` → `{ version: "1.1.88" }`. Déjà consommée par `SettingsHeaderVersion` dans `HeaderActions.tsx` via `metaApi.root()`.
- `Sidebar.tsx` est un composant serveur (pas de directive `'use client'`).

**Jauge VO2 max :**
- Le calcul du point dans `page.tsx` lignes 77-89 utilise :
  ```js
  const angle = -140 + ratio * 280;  // angle CSS (0° = haut, sens horaire)
  const rad = (angle * Math.PI) / 180;
  const x = center + Math.cos(rad) * radius;  // ❌ convention mathématique (0° = droite)
  const y = center + Math.sin(rad) * radius;  // ❌ idem
  ```
- La jauge (`conic-gradient`) utilise la convention CSS (0° = haut, sens horaire), mais `Math.cos/sin` utilisent la convention mathématique (0° = droite, sens anti-horaire, Y vers le haut).
- Le point est rendu avec `left`/`top` CSS + `-translate-x-1/2 -translate-y-1/2` pour centrage.
- Vérification concrète avec VO2 max = 46 (ratio 0.5, angle CSS = 0° soit le haut du cercle) :
  - Code actuel : `x = 70 + cos(0)*58 = 128` (droite), `y = 70 + sin(0)*58 = 70` (centre) → **position incorrecte** (devrait être en haut : x=70, y=12).
  - Code corrigé : `x = 70 + sin(0)*58 = 70`, `y = 70 - cos(0)*58 = 12` → **position correcte**.

### 3.3 Hypothèses

- Le composant `TrainingLoadChart` réutilise `finiteNumber` déjà défini dans `progress/page.tsx`. La doc source suggère soit d'extraire la fonction dans un utilitaire partagé, soit de la dupliquer. Hypothèse : duplication acceptable pour le scope de cette modification, car le composant est autonome.
- La version applicative (`1.1.88` dans `package.json` frontend) correspond à la version exposée par l'API (`GET /` → `metaApi.root()`). Hypothèse : ces deux sources sont synchronisées.
- Le drawer mobile n'est pas impacté par la réduction de largeur sidebar desktop car il utilise sa propre largeur (`w-[18rem] max-w-[88vw]`).

### 3.4 Incertitudes

- Le `ProgressSeriesRow` retourné par `list_series_rows` est un tuple nommé avec `.start_ts_utc` et `.value`. La doc source utilise `r.value` et `r.start_ts_utc`. Si la structure exacte diffère, l'endpoint training-load devra être adapté.
- L'indexation doit avoir été exécutée au moins une fois pour que `trimp` soit renseigné. Le code existant lance déjà une indexation rapide à l'ouverture de `/progress` (lignes 210-293 de `page.tsx`). Pas de risque pour le calendrier (utilise `distance_m` qui est toujours présent).

## 4. Spécification fonctionnelle cible

### 4.1 Calendrier (Calendar Heatmap)

**Comportement attendu :**
- Carte affichant une heatmap annuelle façon GitHub : grille 7 jours × ~52 semaines.
- Chaque cellule = un jour ; intensité de couleur basée sur le volume (km).
- 3 KPIs : jours actifs dans l'année, plus longue série (streak max), série en cours.
- Sélecteur d'année (année courante et 5 années précédentes).
- Légende de l'échelle de couleur (Moins → Plus).

**États :**
- `loading` : carte avec titre "Calendrier" et texte "Chargement…".
- `empty` (aucune activité dans l'année) : carte avec sélecteur d'année + message "Pas d'activités en YYYY".
- `error` : carte avec message "Données indisponibles".
- `data` : heatmap complète avec KPIs et légende.

**Position dans la page `/progress`** : immédiatement après la carte "Volume hebdo" (ligne 688 de `page.tsx` : après `</Card>` du volume), avant la carte "Charge (TRIMP) par semaine".

### 4.2 Charge d'entraînement (Training Load)

**Comportement attendu :**
- Section avec KPIs (ACWR, Monotonie, Strain) + badge de zone de risque + graphique ComposedChart Recharts.
- Graphique : charge aiguë 7j (aire), charge chronique 42j (ligne grise), ACWR (ligne pointillée orange, axe Y droit), bandes de référence (0.8 vert, 1.3 orange, 1.5 rouge).
- Sélecteur de période (30j, 60j, 90j, 6 mois, 1 an).

**États :**
- `loading` : carte avec titre "Charge d'entraînement" et "Chargement…".
- `empty` (pas de données TRIMP) : message "Pas de données de charge disponibles".
- `error` : message "Données indisponibles".
- `data` : KPIs + badge risque + graphique.

**Position dans la page `/progress`** : immédiatement après la carte "Charge (TRIMP) par semaine" (ligne 727 de `page.tsx`), avant la carte "Best effort" (ligne 729).

### 4.3 Sidebar

**Largeur :** `220px` (réduction de ~15.4% par rapport à 260px, arrondi propre).

**Version :** Affichée sur la même ligne que "CourseScope", avec le style `text-xs text-muted-foreground` (identique au sous-titre). Layout cible :

```
CourseScope v1.1.88            ← CourseScope en text-lg font-semibold, v1.1.88 en text-xs text-muted-foreground
Analyse d'activites de course  ← inchangé
```

### 4.4 Jauge VO2 max

**Comportement attendu :** Le point indiquant la valeur de VO2 max sur la jauge circulaire doit se positionner correctement le long de l'arc coloré, proportionnellement à la valeur (min=30, max=62). Actuellement toujours au maximum → après correction, le point suit la graduation.

## 5. Spécification technique proposée

### 5.1 Frontend

#### 5.1.1 Calendrier — Fichiers à créer/modifier

| # | Fichier | Action | Détail |
|---|---------|--------|--------|
| 1 | `frontend/src/types/api.ts` | Ajouter | Interfaces `CalendarDay` et `CalendarResponse` (en fin de fichier) |
| 2 | `frontend/src/lib/api.ts` | Ajouter | Méthode `progressApi.calendar(year)` + import `CalendarResponse` |
| 3 | `frontend/src/hooks/useProgress.ts` | Ajouter | Query key `calendar` + hook `useCalendar(year)` + import `CalendarResponse` |
| 4 | `frontend/src/components/features/progress/CalendarHeatmap.tsx` | Créer | Composant principal (~290 lignes, basé sur `docs/calendrier-implementation.md` §4.4) |
| 5 | `frontend/src/app/progress/page.tsx` | Modifier | Import + `<CalendarHeatmap />` après la carte Volume hebdo |

**Détail d'implémentation CalendarHeatmap :**
- `'use client'` — utilise `useCalendar` (TanStack Query).
- Échelle de couleur fixe : `bg-gray-100` (0 km), `bg-blue-100` (<3 km), `bg-blue-300` (<8 km), `bg-blue-500` (<15 km), `bg-blue-800` (≥15 km).
- Grille construite en remplissant les jours manquants de l'année avec `has_activity: false`.
- Jours de semaine : Lundi à Dimanche (ISO, `(getUTCDay() + 6) % 7`).
- Tailles de cellule : 13px × 13px, gap 2px.
- Seuils de couleur codés en dur, ajustables.
- Réutilise `formatNumber` de `@/lib/metricsFormat` et `cn` de `@/lib/utils`.
- Utilise les primitives `Card`, `CardContent`, `CardHeader`, `CardTitle` existantes.

#### 5.1.2 Charge d'entraînement — Fichiers à créer/modifier

| # | Fichier | Action | Détail |
|---|---------|--------|--------|
| 1 | `frontend/src/types/api.ts` | Ajouter | Interfaces `TrainingLoadPoint` et `TrainingLoadResponse` |
| 2 | `frontend/src/lib/api.ts` | Ajouter | Méthode `progressApi.trainingLoad(params)` + import |
| 3 | `frontend/src/hooks/useProgress.ts` | Ajouter | Query keys + hook `useTrainingLoad(params)` + import |
| 4 | `frontend/src/components/features/progress/TrainingLoadChart.tsx` | Créer | Composant principal (~310 lignes, basé sur `docs/charge-entrainement-implementation.md` §4.4) |
| 5 | `frontend/src/app/progress/page.tsx` | Modifier | Import + `<TrainingLoadChart />` après la carte Charge TRIMP |

**Détail d'implémentation TrainingLoadChart :**
- `'use client'` — utilise `useTrainingLoad` (TanStack Query).
- Graphique `ComposedChart` Recharts avec :
  - `Area` pour charge aiguë 7j (couleur `#0f172a`, fillOpacity 0.08).
  - `Line` pour charge chronique 42j (couleur `#64748b`).
  - `Line` pour ACWR sur axe Y droit (couleur `#f4a261`, `strokeDasharray="4 4"`).
  - `ReferenceLine` × 3 pour les seuils ACWR (0.8, 1.3, 1.5).
- KPIs dans 3 mini-cards (ACWR, Monotonie, Strain).
- Badge de zone de risque : `Faible` (vert), `Modéré` (jaune), `Élevé` (rouge).
- Sélecteur de période (30/60/90/180/365 jours) — filtre côté client sur `data.points.slice(-days)`.
- Fonction `finiteNumber` dupliquée dans le composant (ou extraite si refacto futur).
- Réutilise Recharts (déjà installé), `Card`, `cn`, `formatNumber`.

#### 5.1.3 Sidebar — Fichiers à modifier

| # | Fichier | Action | Détail |
|---|---------|--------|--------|
| 1 | `frontend/src/components/layout/AppShell.tsx` | Modifier | `md:grid-cols-[260px_minmax(0,1fr)]` → `md:grid-cols-[220px_minmax(0,1fr)]` |
| 2 | `frontend/src/components/layout/Sidebar.tsx` | Modifier | Ajouter prop `version?: string`, afficher à côté du titre |

**Détail Sidebar :**
- Nouvelle prop : `version?: string`.
- Dans le bloc branding (lignes 17-19), remplacer :
  ```tsx
  <p className="text-lg font-semibold tracking-tight">CourseScope</p>
  ```
  par :
  ```tsx
  <p className="text-lg font-semibold tracking-tight">
    CourseScope
    {version ? <span className="ml-1.5 text-xs font-normal text-muted-foreground">v{version}</span> : null}
  </p>
  ```
- `AppShell.tsx` doit fournir la version. Ajouter un `useQuery` sur `metaApi.root()` dans AppShell (déjà `'use client'`) et passer `version={versionQuery.data?.version}` à `<Sidebar>`.

**Note sur l'import `metaApi`** : `AppShell.tsx` devra importer `metaApi` depuis `@/lib/api` et `useQuery` depuis `@tanstack/react-query`.

#### 5.1.4 Jauge VO2 max — Fichier à modifier

| # | Fichier | Action | Détail |
|---|---------|--------|--------|
| 1 | `frontend/src/app/page.tsx` | Modifier | Lignes 86-87 : corriger la conversion angle CSS → coordonnées écran |

**Correction exacte :**

Remplacer (lignes 86-87) :
```tsx
const x = center + Math.cos(rad) * radius;
const y = center + Math.sin(rad) * radius;
```
Par :
```tsx
const x = center + Math.sin(rad) * radius;
const y = center - Math.cos(rad) * radius;
```

**Justification mathématique :** L'angle `-140 + ratio * 280` est en convention CSS (0° = haut du cercle, sens horaire). La conversion en coordonnées écran (x croissant vers la droite, y croissant vers le bas) est : `x = center + sin(θ) × radius`, `y = center - cos(θ) × radius`.

Vérification pour angle = 0° (haut du cercle, ratio = 0.5, VO2 ≈ 46) :
- `x = 70 + sin(0) × 58 = 70` (centre horizontal) ✓
- `y = 70 - cos(0) × 58 = 12` (proche du haut) ✓

### 5.2 Backend

#### 5.2.1 Endpoint `GET /progress/calendar`

**Fichier** : `backend/api/routes/progress.py`

**Ajouter** après les endpoints existants (après `/progress/session-taxonomy` ou en fin de fichier) :

```python
@router.get("/progress/calendar")
async def get_calendar(
    request: Request,
    year: int = Query(..., ge=2000, le=2100),
):
    """Données de heatmap calendrier pour une année donnée."""
```

**Logique** :
1. Récupérer `db_session_factory` depuis `request.app.state`.
2. Appeler `ProgressRepository.list_activity_rows()` avec `from_ts_utc=f"{year}-01-01T00:00:00Z"`, `to_ts_utc=f"{year}-12-31T23:59:59Z"`, `activity_type="real"`, `limit=None`.
3. Agréger par jour (clé = `start_ts_utc[:10]`) : somme `distance_m` → `distance_km`, somme `moving_time_s`, compteur `activity_count`.
4. Calculer les streaks via `_compute_streaks(active_dates, today_iso)`.
5. Retourner `{ days, year, total_active_days, longest_streak, current_streak }`.

**Fonction helper `_compute_streaks`** : définie comme fonction privée dans le module. Calcule la plus longue série de jours consécutifs actifs et la série en cours (en remontant depuis aujourd'hui).

**Dépendances déjà satisfaites** : `ProgressRepository`, `list_activity_rows`, `datetime`, `timedelta`, `timezone`, `math` — tous déjà importés.

#### 5.2.2 Endpoint `GET /progress/training-load`

**Fichier** : `backend/api/routes/progress.py`

**Ajouter** après les endpoints existants :

```python
@router.get("/progress/training-load")
async def get_training_load(
    request: Request,
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
):
    """ACWR, monotonie d'entraînement, et strain à partir de la série TRIMP."""
```

**Logique** :
1. Récupérer `db_session_factory`.
2. Parser `from_ts`/`to_ts` via `_parse_ts_utc()`.
3. Appeler `ProgressRepository.list_series_rows(metric="trimp", ...)`.
4. Bucketer TRIMP par jour.
5. Pour chaque jour, calculer :
   - **Charge aiguë (7j)** : moyenne glissante sur 7 jours.
   - **Charge chronique (42j)** : moyenne glissante sur 42 jours (si ≥7 jours disponibles).
   - **ACWR** : aiguë / chronique.
   - **Monotonie (7j)** : moyenne / écart-type (si ≥3 valeurs, écart-type > 0).
   - **Strain (7j)** : somme TRIMP × monotonie.
6. Déterminer `risk_zone` à partir de l'ACWR le plus récent (<0.8 → "low", 0.8-1.3 → "moderate", ≥1.3 → "high").
7. Retourner `{ points, current_acwr, current_monotony, current_strain, risk_zone }`.

**Dépendances déjà satisfaites** : `ProgressRepository`, `list_series_rows`, `_parse_ts_utc`, `math.sqrt`, `math.isfinite`.

#### 5.2.3 Compatibilité API

Les deux nouveaux endpoints doivent être accessibles via `/progress/calendar` ET `/api/progress/calendar` (idem pour training-load). La règle de compatibilité `/xxx` et `/api/xxx` est gérée par le montage du router FastAPI et le proxy Next.js — aucune action supplémentaire n'est requise.

### 5.3 Données et métriques

| Champ | Unité | Null possible ? | Fallback |
|-------|-------|-----------------|----------|
| `CalendarDay.distance_km` | km | Oui (si pas d'activité) | `null` |
| `CalendarDay.moving_time_s` | secondes | Oui | `null` |
| `CalendarResponse.total_active_days` | jours (entier) | Non | — |
| `CalendarResponse.longest_streak` | jours (entier) | Non (min 0) | — |
| `TrainingLoadPoint.acute_load_7d` | TRIMP/jour | Non (arrondi 1 décimale) | — |
| `TrainingLoadPoint.chronic_load_42d` | TRIMP/jour | Oui (si <7j de données) | `null` |
| `TrainingLoadPoint.acwr` | ratio | Oui (si chronique ≤0) | `null` |
| `TrainingLoadPoint.monotony_7d` | ratio | Oui (si écart-type ≤0) | `null` |
| `TrainingLoadPoint.strain_7d` | TRIMP | Oui (si monotonie nulle) | `null` |

### 5.4 Documentation

La documentation suivante devra être mise à jour (après implémentation, si demandé) :
- `docs/metrics_catalog.md` : ajouter Calendrier et Training Load.
- `docs/metrics_list.txt` : ajouter les nouveaux endpoints.

**Justification** : nouvelles métriques exposées par l'API → documentation nécessaire. Mais selon `AGENTS.md` §5.6, ne pas modifier sans demande explicite. L'agent-dev devra confirmer avant de toucher à la documentation.

## 6. Plan d'implémentation pour agent-dev

### Étape 1 — Backend : endpoint `/progress/calendar`

- **Objectif** : Ajouter l'endpoint GET `/progress/calendar?year=YYYY` avec calcul des streaks.
- **Fichier** : `backend/api/routes/progress.py`
- **Détails** : Ajouter la fonction helper `_compute_streaks` et le handler `get_calendar` (cf. `docs/calendrier-implementation.md` §3.1).
- **Tests** : Vérifier avec `curl "http://127.0.0.1:8000/progress/calendar?year=2026"`. Lancer `python -m compileall backend`.
- **Risques** : Aucun. Lecture seule sur table existante, pas de migration.

### Étape 2 — Backend : endpoint `/progress/training-load`

- **Objectif** : Ajouter l'endpoint GET `/progress/training-load?from=&to=` avec calcul ACWR/Monotonie/Strain.
- **Fichier** : `backend/api/routes/progress.py`
- **Détails** : Ajouter le handler `get_training_load` (cf. `docs/charge-entrainement-implementation.md` §3.1).
- **Tests** : `curl "http://127.0.0.1:8000/progress/training-load"`. Lancer `python -m compileall backend`.
- **Risques** : Si `ProgressSeriesRow` n'a pas `.value` et `.start_ts_utc` comme supposé, vérifier la structure réelle et adapter.

### Étape 3 — Frontend : types API + méthode API + hooks (Calendrier)

- **Objectif** : Ajouter les types, la méthode API et le hook React Query pour le calendrier.
- **Fichiers** : `frontend/src/types/api.ts`, `frontend/src/lib/api.ts`, `frontend/src/hooks/useProgress.ts`
- **Détails** : 
  - Types `CalendarDay` et `CalendarResponse` en fin de `api.ts`.
  - `progressApi.calendar(year)` dans `lib/api.ts`.
  - `progressKeys.calendar(year)` + `useCalendar(year)` dans `useProgress.ts`.
- **Tests** : `cd frontend && npm run build`.
- **Risques** : Aucun. Ajouts incrémentaux.

### Étape 4 — Frontend : types API + méthode API + hooks (Training Load)

- **Objectif** : Ajouter les types, la méthode API et le hook pour la charge d'entraînement.
- **Fichiers** : `frontend/src/types/api.ts`, `frontend/src/lib/api.ts`, `frontend/src/hooks/useProgress.ts`
- **Détails** :
  - Types `TrainingLoadPoint` et `TrainingLoadResponse`.
  - `progressApi.trainingLoad(params)`.
  - `progressKeys.trainingLoad()`, `progressKeys.trainingLoadQuery(params)`, `useTrainingLoad(params)`.
- **Tests** : `cd frontend && npm run build`.
- **Risques** : Aucun.

### Étape 5 — Frontend : composant CalendarHeatmap.tsx

- **Objectif** : Créer le composant CalendarHeatmap avec heatmap, KPIs, sélecteur d'année.
- **Fichier** : `frontend/src/components/features/progress/CalendarHeatmap.tsx` (créer)
- **Détails** : Implémenter selon `docs/calendrier-implementation.md` §4.4. Gérer les états loading/error/empty.
- **Tests** : `cd frontend && npm test && npm run build`.
- **Risques** : Si le dossier `features/progress/` n'existe pas, le créer.

### Étape 6 — Frontend : composant TrainingLoadChart.tsx

- **Objectif** : Créer le composant TrainingLoadChart avec KPIs, graphique ACWR, badge risque.
- **Fichier** : `frontend/src/components/features/progress/TrainingLoadChart.tsx` (créer)
- **Détails** : Implémenter selon `docs/charge-entrainement-implementation.md` §4.4. Gérer les états loading/error/empty.
- **Tests** : `cd frontend && npm test && npm run build`.
- **Risques** : `finiteNumber` est dupliquée dans le composant (déjà présente dans `page.tsx`). Acceptable pour ce scope.

### Étape 7 — Frontend : intégration dans la page /progress

- **Objectif** : Insérer `<CalendarHeatmap />` après Volume hebdo, `<TrainingLoadChart />` après Charge TRIMP.
- **Fichier** : `frontend/src/app/progress/page.tsx`
- **Détails** :
  - Importer les deux composants.
  - `<CalendarHeatmap />` après la fermeture `</Card>` du Volume hebdo (ligne 688).
  - `<TrainingLoadChart />` après la fermeture `</Card>` du Charge TRIMP (ligne 727).
- **Tests** : `cd frontend && npm test && npm run build`.
- **Risques** : Vérifier que les imports n'entrent pas en conflit avec les imports existants.

### Étape 8 — Frontend : réduction sidebar + version

- **Objectif** : Réduire la largeur sidebar à 220px et afficher la version.
- **Fichiers** : `frontend/src/components/layout/AppShell.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Détails** :
  - `AppShell.tsx` ligne 49 : `260px` → `220px`.
  - `AppShell.tsx` : ajouter `useQuery` sur `metaApi.root()`, passer `version` à `<Sidebar>`.
  - `Sidebar.tsx` : ajouter prop `version?: string`, afficher dans le bloc branding.
- **Tests** : `cd frontend && npm run build`. Vérifier visuellement la sidebar.
- **Risques** : La largeur 220px peut dégrader la lisibilité des libellés de navigation sur écrans étroits. Test recommandé.

### Étape 9 — Frontend : correction jauge VO2 max

- **Objectif** : Corriger le positionnement du point sur la jauge VO2 max.
- **Fichier** : `frontend/src/app/page.tsx`
- **Détails** : Remplacer lignes 86-87 (cf. §5.1.4 ci-dessus).
- **Tests** : `cd frontend && npm test && npm run build`. Vérifier visuellement avec différentes valeurs de VO2 max.
- **Risques** : Aucun. Changement localisé de 2 lignes.

## 7. Tests et vérifications attendus

### Backend

```bash
python -m compileall backend
python -m pytest tests/pytest/ -x -q
python -m pytest tests/unit/ -x -q
```

Vérifications manuelles :
```bash
curl "http://127.0.0.1:8000/progress/calendar?year=2026"
curl "http://127.0.0.1:8000/progress/training-load"
curl "http://127.0.0.1:8000/progress/training-load?from=2026-01-01&to=2026-06-30"
```

### Frontend

```bash
cd frontend
npm test
npm run build
```

Vérifications manuelles :
- Page `/progress` : calendrier et charge d'entraînement apparaissent aux bonnes positions.
- Page `/progress` : changer l'année du calendrier, changer la période du training load.
- Page `/progress` : états loading/empty/error (tester sans données).
- Page `/` : la jauge VO2 max affiche le point à la bonne position (tester avec différentes valeurs).
- Sidebar desktop : largeur réduite, version affichée.
- Sidebar mobile : drawer non impacté.
- Toutes les pages : pas de régression UI.

## 8. Critères d'acceptation

- [ ] L'endpoint `GET /progress/calendar?year=YYYY` retourne les données de heatmap avec streaks.
- [ ] L'endpoint `GET /progress/training-load` retourne ACWR, monotonie, strain.
- [ ] Le composant `CalendarHeatmap` s'affiche sous "Volume hebdo" dans `/progress` avec heatmap interactive.
- [ ] Le composant `TrainingLoadChart` s'affiche sous "Charge (TRIMP) par semaine" dans `/progress` avec graphique ACWR.
- [ ] Les deux composants gèrent les états loading, error, et empty.
- [ ] La sidebar desktop fait 220px de large (contre 260px avant).
- [ ] La version (ex: `v1.1.88`) est affichée à côté de "CourseScope" dans la sidebar, en `text-xs text-muted-foreground`.
- [ ] La jauge VO2 max positionne son point correctement (pas toujours au max).
- [ ] `npm run build` passe sans erreur.
- [ ] `python -m compileall backend` passe sans erreur.
- [ ] Aucune duplication de header/container dans les nouveaux composants.
- [ ] Le drawer mobile fonctionne toujours.
- [ ] Les endpoints sont accessibles en `/progress/calendar` et `/api/progress/calendar` (idem training-load).

## 9. Risques et garde-fous

### Risque 1 — Structure de `ProgressSeriesRow`
**Garde-fou** : Vérifier dans `progress_repository.py` que les rows retournées ont bien `.value` et `.start_ts_utc`. Si nom différent, adapter le code de l'endpoint training-load.

### Risque 2 — TRIMP non renseigné
**Garde-fou** : L'indexation rapide est lancée automatiquement à l'ouverture de `/progress`. Si `trimp` est null pour toutes les activités, le graphique affichera "Pas de données de charge disponibles" — état géré.

### Risque 3 — Sidebar à 220px et lisibilité
**Garde-fou** : Les libellés de navigation français ("Page d'accueil", "Progression", "Traces GPX") sont testés à 220px. Si trop étroit, ajuster à 230px. Le `text-xs` du sous-titre peut être réduit à `text-[11px]` si nécessaire.

### Risque 4 — Régressions dans la page /progress
**Garde-fou** : Les ajouts sont localisés (2 composants ajoutés après le contenu existant, pas de refacto). Les composants existants ne sont pas modifiés. Si un test échoue, vérifier que les nouveaux imports n'entrent pas en conflit.

### Risque 5 — Fuseau horaire dans le calendrier
**Garde-fou** : Les dates sont en UTC (`start_ts_utc`). La heatmap utilise UTC pour éviter les décalages. Si l'utilisateur est en France (UTC+2), un run à 23h UTC apparaitra le jour J+1 en heure locale. Documenté mais acceptable pour une heatmap annuelle.

## 10. Décisions prises par agent-brainstorm

1. **Largeur sidebar arrondie à 220px** (au lieu de 221px exact) : 1px de différence est négligeable (0.4%), et 220px est plus propre en CSS.
2. **Version affichée sur la même ligne que le titre** : "CourseScope v1.1.88" sur une ligne, sous-titre inchangé en dessous. Plus compact et suit l'esprit de la demande ("à la suite du titre").
3. **Version récupérée via `useQuery` dans AppShell** : plutôt que de convertir Sidebar en composant client, on garde Sidebar simple et on passe la version en prop depuis AppShell (déjà `'use client'`).
4. **Option A (ajout inline) pour les deux composants** : pas de refacto par onglets. La page `/progress` fait déjà 1200 lignes — un refacto par onglets est souhaitable mais hors scope. Les docs sources mentionnent cette option comme la plus simple.
5. **`finiteNumber` dupliquée dans TrainingLoadChart** : plutôt que d'extraire dans un utilitaire partagé (refacto qui toucherait `page.tsx`), on duplique la fonction dans le nouveau composant. Cohérent avec le principe "changer le minimum nécessaire".
6. **Pas de modification de `docs/`** : la mise à jour de `metrics_catalog.md` et `metrics_list.txt` est laissée à l'appréciation de l'utilisateur après validation.

## 11. Points à ne pas faire

- **Ne pas refactorer `/progress` en onglets** : option B des docs sources. Hors scope, trop risqué pour cette itération.
- **Ne pas modifier le drawer mobile** : sa largeur (`w-[18rem] max-w-[88vw]`) est indépendante de la sidebar desktop.
- **Ne pas modifier `docs/modifications.txt`** : c'est le fichier d'entrée utilisateur.
- **Ne pas modifier les endpoints existants** : `/progress/series`, `/progress/activities`, etc. restent inchangés.
- **Ne pas ajouter de dépendance npm** : Recharts, TanStack Query, Tailwind sont déjà installés.
- **Ne pas modifier la navigation (`nav.ts`)** : pas d'ajout de page.
- **Ne pas modifier les métadonnées de page (`page-metadata.tsx`)** : la page `/progress` garde son title/subtitle/container actuels.
- **Ne pas extraire `finiteNumber` dans un utilitaire partagé** : refacto hors scope, nécessiterait de modifier `page.tsx` existant.
- **Ne pas modifier le comportement de l'indexation automatique** dans `/progress`.
- **Ne pas changer les tokens de design** : les nouveaux composants utilisent `bg-card`, `text-muted-foreground`, `border`, etc.
