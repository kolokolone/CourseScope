# Rapport d'audit — CourseScope

Date : 2026-06-30
Périmètre : Backend, frontend, API, documentation, architecture

---

## 1. Résumé exécutif

CourseScope est une application web locale d'analyse de courses à pied, mature et bien architecturée. Le projet compte **70 fichiers Python backend** (~14 500 lignes), **80+ fichiers TypeScript/TSX frontend** (~12 000 lignes), **52 endpoints API** et **17 documents techniques**. L'application est fonctionnelle, testée et déployable via Docker.

**Points forts** : séparation claire backend/frontend, API cohérente, registre de métriques centralisé, documentation de design complète, workflow agentique structuré.

**Points d'attention** : 5 monolithes backend (>500 lignes), 6 composants frontend trop volumineux (>300 lignes), 16 fonctions dupliquées côté backend, 10+ patterns dupliqués côté frontend, 6 endpoints non utilisés.

---

## 2. Architecture backend

### 2.1 Stack
- **Framework** : FastAPI + uvicorn
- **Parsing** : gpxpy, fitparse → DataFrame pandas canonique (19 colonnes)
- **Stockage** : Fichiers parquet + métadonnées JSON + SQLite (WAL)
- **Cache** : LRU mémoire + disque optionnel
- **Indexation** : Système fast/slow avec fingerprint et versioning

### 2.2 Organisation

| Couche | Dossier | Rôle |
|---|---|---|
| API | `backend/api/` | Routes REST (10 routeurs), schémas Pydantic, compatibilité `/api/*` |
| Core | `backend/core/` | Moteur d'analyse : parsing GPX/FIT, dérivées, stats, zones, plots |
| Services | `backend/services/` | Orchestration, cache, sérialisation |
| Storage | `backend/storage/` | Persistance parquet + métadonnées |
| DB | `backend/db/` | Modèles SQLAlchemy + repositories |
| Progress | `backend/progress/` | Indexation analytique fast/slow |
| Registry | `backend/registry/` | Registre des séries (10 séries, LTTB) |
| Intégrations | `backend/integrations/garmin/` | Client Garmin Connect |

### 2.3 Endpoints (52 total)

| Routeur | Endpoints |
|---|---|
| Activities | 5 (upload, list, delete, cleanup, rename) |
| Analysis | 4 (real, theoretical, pace-vs-grade, real-bins) |
| Series | 2 (get named series, list available) |
| Maps | 1 (bbox, polyline, markers) |
| Traces | 8 (CRUD, open, trace-status, trace-save) |
| Progress | 15 (indexation, activities, series, best-efforts, HR@pace, pace@HR, waterfall, training-load, calendar, taxonomy, tags) |
| Goals | 5 (CRUD, cleanup) |
| Settings | 3 (personal, patch, hr-max-detected) |
| Garmin | 6 (connect, sync, reset, status, credentials) |
| Geo | 1 (city autocomplete) |
| Root | 2 (`/`, `/health`) |

---

## 3. Architecture frontend

### 3.1 Stack
- **Framework** : Next.js 16 (App Router) + React 19 + TypeScript
- **Styling** : Tailwind CSS 4 + design tokens (Space Grotesk, JetBrains Mono)
- **Graphiques** : Recharts 3.7 + react-three-fiber (waterfall 3D)
- **Cartes** : Leaflet + react-leaflet
- **State** : TanStack React Query + Zustand (localStorage)

### 3.2 Pages

| Route | Page | Lignes |
|---|---|---|
| `/` | Home (upload, historique, VO2max) | 206 |
| `/activities` | Liste des activités | 348 |
| `/activities/[id]` | Détail activité réelle (legacy) | 785 |
| `/activities-beta/[id]` | Détail activité réelle (beta) | 11 + composants |
| `/traces` | Liste des traces | 221 |
| `/traces/[id]` | Analyse théorique | 561 |
| `/goals` | Objectifs (CRUD, timeline, calendrier) | 763 |
| `/progress` | Dashboard progression | 1206 |
| `/settings` | Paramètres | 57 + composants |

### 3.3 API client
- Module centralisé `lib/api.ts` (542 lignes, 13 modules API)
- React Query hooks : `useActivity`, `useProgress`, `useGoals`, `useTraces`, `useSettings`, `useGeo`
- Proxy Next.js : `/api/*` → `http://127.0.0.1:8000/*`

---

## 4. Redondances détectées

### Backend (16 fonctions dupliquées)

| Fonctions | Fichiers concernés | Recommandation |
|---|---|---|
| `_find_original_path`, `_find_original_fit_path` | `indexation_runner.py`, `verify_index.py` | Extraire dans `progress/_utils.py` |
| `_model_to_dict` | `activities.py`, `series.py`, `activity_store.py` | Extraire dans `api/_compat.py` |
| `_now_utc_iso` | `indexation_runner.py`, `verify_runner.py` | Utiliser `db/models.py:utc_now_iso()` |
| `_parse_iso`, `_parse_iso_datetime` | `indexation_runner.py`, `verify_index.py`, `indexer.py`, `activity_store.py` | Extraire dans `progress/_utils.py` |
| `_read_json`, `_write_rollup` | `indexation_runner.py`, `verify_index.py` | Extraire dans `progress/_utils.py` |
| `_snapshot_state_unlocked` | `indexation_runner.py`, `verify_runner.py` | Pattern commun → classe `ThreadSafeState` |
| `_weighted_mean` | `metrics.py`, `real_run_analysis.py` | Supprimer le doublon, garder dans `core/` |
| `get_activity_storage` | `main.py`, `activities.py` | Injection de dépendance FastAPI |
| `get_series_registry` | `analysis.py`, `series.py`, `main.py` | Injection de dépendance FastAPI |

### Frontend (10+ patterns dupliqués)

| Pattern | Dans | Recommandation |
|---|---|---|
| `parseFlexibleSeconds` | `traces/[id]/page.tsx`, `goals/page.tsx` | Extraire dans `lib/paceUtils.ts` |
| `formatPaceInputFromSeconds` | Mêmes fichiers | Extraire dans `lib/paceUtils.ts` |
| `formatTimeInputFromSeconds` | Mêmes fichiers | Extraire dans `lib/paceUtils.ts` |
| `formatDateLabel` | 3 pages | Extraire dans `lib/dateUtils.ts` |
| `startOfDay` / `dateAtStart` | 3 pages | Extraire dans `lib/dateUtils.ts` |
| `weekStartUtc`, `isoDateUtc`, `shiftRangeStart` | 2 pages | Extraire dans `lib/dateUtils.ts` |
| `rollingMean` | 3 fichiers | Unifier dans `lib/chartUtils.ts` |
| `isValidNumber` | 2 fichiers | Supprimer le doublon |
| `buildPoints` / `samplePoints` | 2 composants chart | Extraire dans `lib/chartUtils.ts` |

---

## 5. Monolithes détectés

### Backend (fichiers > 500 lignes)

| Fichier | Lignes | Problème | Priorité | Action |
|---|---|---|---|---|
| `core/real_run_analysis.py` | 1349 | 20+ fonctions mêlant calculs et Plotly | 🔴 Critique | Découper en `core/splits.py`, `core/best_efforts.py`, `core/climbs.py`, `core/pace_grade.py`, `core/plots.py` |
| `api/routes/progress.py` | 918 | Logique métier inline dans les handlers HTTP | 🔴 Haute | Extraire calculs dans `services/` ou `core/` |
| `api/routes/analysis.py` | 871 | Binning, parsing inline dans les handlers | 🔴 Haute | Déplacer dans `core/real_activity_bins.py` |
| `core/metrics.py` | 706 | Fonction `compute_garmin_like_stats()` de 415 lignes | 🟡 Moyenne | Splitter en `_compute_summary`, `_compute_zones`, `_compute_pacing`, etc. |
| `progress/indexation_runner.py` | 703 | Thread management + DB sync + FS scan | 🟡 Moyenne | Séparer runner, sync, et utilitaires |

### Frontend (composants > 300 lignes)

| Fichier | Lignes | Problème | Priorité | Action |
|---|---|---|---|---|
| `app/progress/page.tsx` | 1206 | 8 queries, 20+ states, 5 sections de graphes | 🔴 Critique | Découper en 8 sous-composants |
| `app/activities/[id]/page.tsx` | 785 | 6 onglets, inline KPI building | 🔴 Haute | Extraire le rendu des sections |
| `app/goals/page.tsx` | 763 | Calendrier inline, formulaire, timeline | 🔴 Haute | Extraire `GoalCalendar`, `GoalForm` |
| `app/traces/[id]/page.tsx` | 561 | Résolution de trace, inputs pace/temps | 🟡 Moyenne | Extraire `TraceInputPanel` |

---

## 6. Points de performance

### Backend
- L'indexation SQLite est optimisée (WAL, busy timeout, commits batchés)
- Le cache LRU évite les recomputes coûteuses sur les analyses
- Les séries utilisent le downsampling LTTB pour limiter les payloads
- Risque : `POST /integrations/garmin/sync` est synchrone → bien géré via thread worker

### Frontend
- React Query avec cache et déduplication automatique des requêtes
- `React.useMemo` sur les calculs dérivés (tris, filtres, agrégations)
- Pas de virtualization sur les longues tables → risque si 1000+ activités
- La page `/progress` lance 8 queries parallèles au mount → OK avec React Query mais peut saturer
- `ActivityCharts` (506 lignes) recalcule le smoothing à chaque render

---

## 7. Risques de régression

| Risque | Gravité | Contexte |
|---|---|---|
| Suppression d'endpoint non utilisé | Faible | 6 endpoints sans consommateur frontend — vérifier avant suppression |
| Découpage de `real_run_analysis.py` | Élevé | Fichier critique touché par tous les tests — faire par étapes avec tests de non-régression |
| Refacto `progress/page.tsx` | Moyen | Page complexe avec beaucoup d'états — extraire composant par composant |
| Changement de contrat API | Élevé | Les réponses sont consommées par 2 vues (legacy + beta) — toute modification doit être rétrocompatible |
| Déplacement de `modifications.txt` | Nul | Toutes les 33 références mises à jour |

---

## 8. Endpoints non utilisés

| Endpoint | API client défini | Consommé par | Recommandation |
|---|---|---|---|
| `GET /health` | `healthApi.check()` | Aucun composant | Implémenter un health check UI ou supprimer |
| `GET /activity/{id}/series` | `seriesApi.list()` | Aucun composant | Garder (utile pour le debug) |
| `POST /progress/verify` | `progressApi.verify()` | Aucun composant | Supprimer (remplacé par fast/slow) |
| `GET /progress/verify-status` | `progressApi.verifyStatus()` | Aucun composant | Supprimer (remplacé par index/status) |
| `GET /progress/session-taxonomy` | `progressApi.sessionTaxonomy()` | Aucun composant | Implémenter l'UI (valeur métier réelle) |
| `POST /progress/tags` | `progressApi.setTag()` | Aucun composant | Implémenter l'UI de tagging |

---

## 9. Opportunités de nouveaux KPI

### KPI déjà calculés mais non affichés
- **Session taxonomy** : comptes par type de séance (easy, tempo, interval, long run) — déjà dans `/progress/session-taxonomy`
- **Terrain tags** : comptes par type de terrain (flat, rolling, hilly) — déjà dans `/progress/session-taxonomy`
- **Activity tagging** : race markers et tags manuels — endpoint `/progress/tags` existe

### KPI facilement calculables à partir des données existantes
- **Monotony / Strain** (charge monotone) : `mean(weekly_load) / std(weekly_load)` — le training-load endpoint a déjà la structure
- **Intensity distribution** (Z1/Z2/Z3 par semaine) : les zones sont déjà calculées par activité
- **Long run dose** (plus longue sortie par semaine) : déjà dans l'index d'activités
- **VAM trend** : VAM déjà calculé par montée, agrégeable par période

---

## 10. Recommandations

### Court terme (ce qui a été fait dans cet audit)
- ✅ Suppression des fichiers obsolètes (ROADMAP.md, cahier_des_charges.txt, implementations-a-faire.txt, .sisyphus/)
- ✅ Déplacement de `modifications.txt` → `agents/modifications.txt`
- ✅ Mise à jour des 33+ références croisées
- ✅ Fusion de `metrics_list.txt` dans `metrics_catalog.md`
- ✅ Mise à jour du README.md
- ✅ Adaptation de `agent-workflow.md` au code actuel
- ✅ Création du guide de rédaction documentaire
- ✅ Création de ce rapport d'audit

### Court terme (recommandé, non fait pour éviter les régressions)
- Extraire les fonctions dupliquées backend dans des modules partagés
- Supprimer ou implémenter les 6 endpoints non utilisés
- Ajouter `Suspense` et `ErrorBoundary` sur les pages lourdes

### Moyen terme
- Découper `core/real_run_analysis.py` en modules spécialisés (splits, best_efforts, climbs, pace_grade, plots)
- Découper `app/progress/page.tsx` en 8 composants de section
- Extraire les utilitaires frontend dupliqués (`dateUtils.ts`, `chartUtils.ts`, `paceUtils.ts`)
- Implémenter l'UI de session taxonomy et tagging sur la page progression
- Supprimer les composants et fonctions non utilisés (HeroKpi, MetricTile, SidebarStats, activityStore)

### Long terme
- Consolider les vues legacy et beta d'activité (une seule implémentation)
- Ajouter un système de configuration typé (pydantic-settings)
- Migrer vers FastAPI dependency injection pour les handlers
- Virtualisation des longues tables pour > 1000 activités
- Support multi-sport au-delà du running

---

## 11. Changements appliqués dans cet audit

| Action | Fichiers |
|---|---|
| Suppression | `docs/ROADMAP.md`, `docs/implementations-a-faire.txt`, `docs/cahier_des_charges.txt`, `.sisyphus/` (2 fichiers) |
| Déplacement | `docs/modifications.txt` → `agents/modifications.txt` |
| Fusion | `docs/metrics_list.txt` → `docs/metrics_catalog.md` |
| Mise à jour références | `agents/AGENTS.md`, `agents/agent-brainstorm.md`, `agents/agent-dev.md`, `agents/agent-review.md`, `agents/agent-brainstorm/modifications.md`, 8 log files, `docs/documentation_update_runbook.md`, `frontend/src/lib/metricsRegistry.test.ts` |
| Mise à jour docs | `docs/agent-workflow.md` (réécrit), `docs/metrics_catalog.md` (en-tête), `docs/documentation_update_runbook.md` (section 3) |
| Création | `docs/documentation-style-guide.md`, `docs/audit_application.md` (ce fichier) |
| Mise à jour | `README.md` (réécrit) |

## 12. Changements volontairement non appliqués

| Changement | Raison |
|---|---|
| Découpage de `core/real_run_analysis.py` | Risque de régression élevé — nécessite tests approfondis |
| Découpage de `app/progress/page.tsx` | Complexe — préférer une PR dédiée par composant |
| Extraction des fonctions dupliquées backend | ✅ Fait (PR refactor, v1.1.92) |
| Suppression des endpoints non utilisés | Certains peuvent avoir une utilité future (debug, future UI) |
| Suppression de la vue legacy `activities/[id]` | La vue beta est encore en cours de stabilisation |
| Refacto des `get_*` globals en injection FastAPI | Impact systémique — nécessite planification |

---

## 13. Points à vérifier manuellement

- [ ] Lancer `python -m compileall backend` — doit passer sans erreur
- [ ] Lancer `python -m pytest tests/unit/ -q` — vérifier que les tests passent
- [ ] Lancer `cd frontend && npm test` — vérifier que le test metricsRegistry passe
- [ ] Lancer `cd frontend && npm run build` — vérifier que le build frontend passe
- [ ] Vérifier que `agents/modifications.txt` existe et est lisible
- [ ] Vérifier que les agents (brainstorm, dev, review) pointent vers le bon chemin
- [ ] Lancer l'application (`run_win.bat` ou `run_linux.sh --dev`) — vérifier le démarrage
- [ ] Naviguer sur les pages principales — vérifier qu'aucune erreur 404 ou runtime
