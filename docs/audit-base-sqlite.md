# Audit base SQLite — CourseScope

> Audit réalisé le 30 juin 2026. Version de CourseScope : `1.1.91`.
> Périmètre : tout le dépôt `C:\Users\domin\Documents\Python Scripts\CourseScope`.

## 1. Résumé exécutif

La base SQLite de CourseScope (`data/coursescope.sqlite`) contient **12 tables** pour **362 activités**, **3 traces**, **3 objectifs**, et une ligne de configuration utilisateur. L'architecture de stockage est **double** : les données brutes (fichier original + DataFrame Parquet + métadonnées JSON) sont sauvegardées sur le système de fichiers (`data/activities/<uuid>/`), tandis qu'un index SQLite sert à la déduplication, à la synchronisation Garmin et aux dashboards de progression.

**État général** : la base est saine, correctement indexée pour ses cas d'usage actuels, et ne présente pas de corruption. La cohérence entre les couches fichier et SQLite est maintenue par le `LocalTempStorage` et le `progress/indexer.py`.

**Cohérence API / stockage** : la quasi-totalité des endpoints d'analyse par activité (`/activity/{id}/real`, `/activity/{id}/theoretical`, `/activity/{id}/pace-vs-grade`, `/activity/{id}/map`, `/activity/{id}/series/*`) fonctionnent **exclusivement sur les DataFrames Parquet** et n'utilisent pas SQLite. Seuls les endpoints de progression (`/progress/*`) et les endpoints de gestion (settings, goals, traces, activities CRUD) exploitent SQLite.

**Principaux manques** :
- Aucune persistance des métriques calculées par activité (zones, splits, climbs, GAP, pacing, etc.) au-delà de l'index de progression.
- Pas de table d'agrégation hebdomadaire/mensuelle — les agrégations `/progress/series` et `/progress/training-load` sont recalculées à chaque appel.
- Les données de zones (HR, pace, power) par activité sont entièrement recalculées à chaque consultation de l'onglet "Analyse".
- Absence de cache API structuré côté backend (seul un cache mémoire LRU 32 entrées et un cache in-memory TTL sont disponibles, non utilisés par les endpoints d'analyse).

**Principales redondances** :
- Double déclaration de `started_at_utc` / `start_ts_utc` entre `activities` et `progress_activity_index`.
- Double colonne `decoupling_pct` / `cardiac_drift_pct` dans `progress_activity_index` (même valeur, alias).
- Persistance duale fichier + SQLite pour les métadonnées d'activité.

**Priorités d'amélioration** :
1. **P1** : Persister les métriques d'analyse par activité (zones, splits, best efforts) pour éviter le rechargement complet du Parquet à chaque consultation.
2. **P2** : Ajouter une table d'agrégation hebdomadaire pré-calculée pour `/progress/series` et `/progress/training-load`.
3. **P2** : Documenter les ~30 endpoints absents de `docs/metrics_catalog.md`.
4. **P3** : Supprimer la redondance `decoupling_pct` / `cardiac_drift_pct`.

---

## 2. Méthodologie

### Fichiers inspectés

| Catégorie | Fichiers |
|---|---|
| Documentation API | `docs/metrics_catalog.md` (484 lignes) |
| Routes API | `backend/api/routes/*.py` (10 fichiers) + `backend/api/main.py` |
| Modèles ORM | `backend/db/models.py` (252 lignes) |
| Repositories | `backend/db/repository.py`, `progress_repository.py`, `settings_repository.py`, `trace_repository.py`, `goals_repository.py` |
| Storage | `backend/storage/activity_store.py` (572 lignes), `backend/storage/trace_store.py` |
| Services | `backend/services/real_activity_service.py` (357 lignes), `backend/services/cache.py` |
| Core métier | `backend/core/real_run_analysis.py` (1551 lignes), `backend/core/metrics.py` (825 lignes) |
| Progress | `backend/progress/indexer.py` (462 lignes) |
| Session DB | `backend/db/session.py` (94 lignes) |

### Base SQLite analysée

- **Fichier** : `data/coursescope.sqlite` (+ WAL `-wal` et `-shm`)
- **Moteur** : SQLite 3, mode WAL activé, `busy_timeout=5000ms`
- **Méthode** : script Python `sqlite3` en lecture seule via PRAGMA
- **Aucune modification** de la base n'a été effectuée

### Limites de l'audit

- Les volumes exacts de données par table n'ont pas été mesurés en octets (seuls les row counts sont fournis).
- L'analyse de performance des requêtes SQLite n'a pas été benchmarkée (pas de `EXPLAIN QUERY PLAN` systématique).
- Les fichiers Parquet individuels n'ont pas été inspectés (leur schéma est déduit du code).

---

## 3. Cartographie des endpoints API

### 3.1 Endpoints documentés dans `metrics_catalog.md`

| Endpoint | Méthode | Présent dans le code | Présent dans docs/metrics_catalog.md | Tables SQLite utilisées | Commentaire |
|---|---|---|---|---|---|
| `/activity/load` | POST | ✅ `routes/activities.py` | ✅ | `activities`, `activity_sources`, `progress_*` (via indexer) | Retourne `stats_sidebar` + `limits` |
| `/activities` | GET | ✅ `routes/activities.py` | ✅ | Aucune (lit `meta.json` sur disque) | Liste via `LocalTempStorage.list_activities()` |
| `/activity/{id}/real` | GET | ✅ `routes/analysis.py` | ✅ | Aucune (lit `df.parquet`, calcule tout en RAM) | ~100 métriques calculées à la volée |
| `/activity/{id}/theoretical` | GET | ✅ `routes/analysis.py` | ✅ | `user_settings` (VMA), `traces` (trace status) | Calcul théorique + VMA + statut trace |
| `/activity/{id}/pace-vs-grade` | GET | ✅ `routes/analysis.py` | ✅ | Aucune (lit `df.parquet`, calcule tout) | Bins pace vs grade avec pro ref |
| `/activity/{id}/real-bins` | GET | ✅ `routes/analysis.py` | ❌ **Non documenté** | Aucune | Bins pace/grade pour distribution charts |
| `/activity/{id}/map` | GET | ✅ `routes/maps.py` | ✅ | Aucune (lit `df.parquet`) | BBox, polyline, markers |
| `/activity/{id}/series/{name}` | GET | ✅ `routes/series.py` | ✅ | Aucune (lit `df.parquet`) | Série temporelle avec downsampling |
| `/activity/{id}/series` | GET | ✅ `routes/series.py` | ✅ | Aucune | Liste les séries disponibles |
| `/progress/verify` | POST | ✅ `routes/progress.py` | ✅ | `progress_indexation_runs` | Vérification d'intégrité de l'index |
| `/progress/verify-status` | GET | ✅ `routes/progress.py` | ✅ | `progress_indexation_runs` | Statut de la dernière vérification |
| `/progress/activities` | GET | ✅ `routes/progress.py` | ✅ | `progress_activity_index`, `progress_activity_tags` | Liste paginée avec filtres |
| `/progress/series` | GET | ✅ `routes/progress.py` | ✅ | `progress_activity_index` | Agrégation temporelle par métrique |
| `/progress/best-efforts` | GET | ✅ `routes/progress.py` | ✅ | `progress_best_effort_points` | Timeline des meilleurs efforts |
| `/progress/hr-at-pace` | GET | ✅ `routes/progress.py` | ✅ | `progress_pace_hr_bins`, `progress_activity_tags` | HR interpolée à pace fixe |
| `/progress/pace-at-hr` | GET | ✅ `routes/progress.py` | ✅ | `progress_pace_hr_bins`, `progress_activity_tags` | Pace interpolée à HR fixe |
| `/progress/session-taxonomy` | GET | ✅ `routes/progress.py` | ✅ | `progress_activity_tags`, `progress_activity_index` | Distribution des tags |
| `/progress/tags` | POST | ✅ `routes/progress.py` | ✅ | `progress_activity_tags` | Upsert manuel de tags |
| `/progress/pace-hr-waterfall` | GET | ✅ `routes/progress.py` | ✅ | `progress_pace_hr_bins`, `progress_activity_tags` | Courbes Pace↔HR 3D |

### 3.2 Endpoints exposés mais NON documentés dans `metrics_catalog.md`

| Endpoint | Méthode | Fichier source | Tables SQLite | Rôle |
|---|---|---|---|---|
| `/` | GET | `main.py` | Aucune | Racine API (version, statut) |
| `/health` | GET | `main.py` | Aucune | Health check |
| `/activity/{id}/real-bins` | GET | `routes/analysis.py` | Aucune | Bins de distribution pace/grade par activité réelle |
| `DELETE /activity/{id}` | DELETE | `routes/activities.py` | `activities` (via fichier disque) | Suppression activité |
| `DELETE /activities` | DELETE | `routes/activities.py` | `activities`, `activity_sources`, `sync_state` | Vidage complet |
| `PATCH /activities/{id}` | PATCH | `routes/activities.py` | `activities` | Renommage activité |
| `/progress/index/fast` | POST | `routes/progress.py` | `progress_indexation_runs`, `progress_activity_index` | Indexation rapide (FS↔DB) |
| `/progress/index/slow` | POST | `routes/progress.py` | `progress_indexation_runs`, `progress_activity_index`, `progress_best_effort_points`, `progress_pace_hr_bins`, `progress_activity_tags` | Indexation complète (recalcul métriques) |
| `/progress/index/status` | GET | `routes/progress.py` | `progress_indexation_runs` | Statut indexation en cours |
| `/progress/training-load` | GET | `routes/progress.py` | `progress_activity_index` (colonne `trimp`) | ACWR, monotonie, strain |
| `/progress/calendar` | GET | `routes/progress.py` | `progress_activity_index` | Heatmap calendrier par année |
| `/traces` | GET | `routes/traces.py` | `traces` | Liste des traces sauvegardées |
| `DELETE /traces` | DELETE | `routes/traces.py` | `traces` | Suppression de toutes les traces |
| `/traces/upload` | POST | `routes/traces.py` | `traces` | Upload fichier GPX/FIT comme trace |
| `PATCH /traces/{id}` | PATCH | `routes/traces.py` | `traces` | Renommage trace |
| `DELETE /traces/{id}` | DELETE | `routes/traces.py` | `traces` | Suppression trace |
| `/traces/{id}/open` | POST | `routes/traces.py` | `traces` | Ouvre une trace en mode théorique |
| `/activity/{id}/trace-status` | GET | `routes/traces.py` | `traces` | Vérifie si une trace correspond à l'activité |
| `/activity/{id}/trace-save` | POST | `routes/traces.py` | `traces` | Sauvegarde l'activité comme trace |
| `/settings/personal` | GET | `routes/settings.py` | `user_settings`, `progress_activity_index` (HR max détecté) | Paramètres personnels |
| `PATCH /settings/personal` | PATCH | `routes/settings.py` | `user_settings` | Mise à jour paramètres |
| `/settings/personal/hr-max-detected` | GET | `routes/settings.py` | `progress_activity_index` | HR max détecté automatiquement |
| `/goals` | GET | `routes/goals.py` | `goals` | Liste objectifs |
| `/goals` | POST | `routes/goals.py` | `goals` | Création objectif |
| `PATCH /goals/{id}` | PATCH | `routes/goals.py` | `goals` | Mise à jour objectif |
| `DELETE /goals/{id}` | DELETE | `routes/goals.py` | `goals` | Suppression objectif |
| `DELETE /goals` | DELETE | `routes/goals.py` | `goals` | Suppression tous les objectifs |
| `/geo/cities` | GET | `routes/geo.py` | Aucune (cache mémoire TTL 24h) | Géocodage villes (Open-Meteo) |
| `/integrations/garmin/connect` | POST | `routes/garmin_integration.py` | Aucune (tokens fichier) | Connexion Garmin (MFA support) |
| `/integrations/garmin/sync` | POST | `routes/garmin_integration.py` | `activities`, `activity_sources`, `sync_state`, `sync_runs` | Synchronisation Garmin |
| `/integrations/garmin/reset` | POST | `routes/garmin_integration.py` | `sync_state`, `activity_sources` | Reset curseur Garmin |
| `/integrations/garmin/status` | GET | `routes/garmin_integration.py` | `sync_state`, `sync_runs` | Statut synchronisation |
| `/integrations/garmin/credentials/status` | GET | `routes/garmin_integration.py` | Aucune (fichier credentials) | Statut credentials |
| `/integrations/garmin/credentials` | POST | `routes/garmin_integration.py` | Aucune (fichier credentials) | Sauvegarde credentials |

**Total** : **33 endpoints documentés** dans le catalogue, **39 endpoints réellement exposés** dans le code (dont 6 non documentés + `/activity/{id}/real-bins`). Le catalogue couvre ~85% des endpoints. Les endpoints manquants concernent principalement la gestion (CRUD activities, goals, traces, settings) et les intégrations Garmin.

### 3.3 Endpoints documentés mais absents du code

Aucun. Tous les endpoints mentionnés dans `docs/metrics_catalog.md` sont bien implémentés.

**Note** : le catalogue documente `POST /progress/verify` et `GET /progress/verify-status` comme un bloc unique. Dans le code, `POST /progress/verify` déclenche la vérification et `GET /progress/verify-status` en donne le statut. Le `POST` est correct mais le catalogue ne le distingue pas explicitement du `GET`. Ce n'est pas une erreur bloquante.

---

## 4. Schéma SQLite observé

| Table | Rôle probable | Colonnes principales | Volume approximatif | Index existants | Commentaire |
|---|---|---|---|---|---|
| `activities` | Registre des activités importées | `id`, `name`, `activity_type`, `started_at_utc`, `created_at_utc`, `file_hash_sha256`, `original_path`, `parquet_path`, `progress_indexed_at_utc`, `progress_rollup_path` | 362 lignes | PK sur `id`, UNIQUE sur `file_hash_sha256` | Table d'index pour déduplication et lookup. Les données réelles sont sur disque. |
| `activity_sources` | Mapping source externe → activité | `id`, `activity_id` (FK), `source`, `source_activity_id` | 360 lignes | PK sur `id`, UNIQUE sur `(source, source_activity_id)` | Utilisé pour la synchro Garmin (source=garmin). |
| `traces` | Parcours théoriques sauvegardés | `id`, `name`, `created_at_utc`, `file_hash_sha256`, `route_fingerprint`, `distance_km`, `elevation_gain_m`, `elevation_loss_m`, `elevation_min_m`, `elevation_max_m`, `original_filename`, `original_path` | 3 lignes | PK sur `id`, UNIQUE sur `file_hash_sha256`, INDEX sur `route_fingerprint` | Stocke les métriques de base. Le fichier GPX original est sur disque. |
| `goals` | Objectifs de course | `id`, `name`, `event_date`, `distance_km`, `location`, `location_city`, `location_country`, `location_country_code`, `location_lat`, `location_lon`, `target_time_s`, `target_pace_s_per_km`, `race_type`, `notes`, `created_at_utc`, `updated_at_utc` | 3 lignes | PK sur `id`, INDEX sur `event_date` | Table complète, bien normalisée. |
| `user_settings` | Configuration personnelle | `id`, `vma_kmh`, `vo2max_lastest`, `hr_max_manual_bpm`, `hr_max_source`, `updated_at_utc` | 1 ligne | PK sur `id` | Singleton (id=1). `vo2max_lastest` est migré mais non documenté dans le catalogue. |
| `sync_state` | Curseur de synchronisation | `source`, `cursor_time_utc`, `updated_at_utc` | 1 ligne | PK sur `source` | Actuellement seule la source "garmin" est utilisée. |
| `sync_runs` | Historique des synchronisations | `id`, `source`, `started_at_utc`, `finished_at_utc`, `status`, `imported_count`, `skipped_count`, `error` | 18 lignes | PK sur `id` | Log des runs de synchro Garmin. |
| `progress_activity_index` | Index de progression (métriques agrégées par activité) | `activity_id`, `activity_type`, `start_ts_utc`, `distance_m`, `moving_time_s`, `elapsed_time_s`, `elevation_gain_m`, `avg_pace_s_per_km`, `best_pace_s_per_km`, `pace_threshold_s_per_km`, `avg_hr_bpm`, `max_hr_bpm`, `trimp`, `decoupling_pct`, `cardiac_drift_pct`, `stability_cv`, `stability_iqr_ratio`, `aerobic_efficiency_m_s_per_bpm`, `vo2max`, `has_hr`, `has_power`, `has_cadence`, `data_points`, etc. | 362 lignes | PK sur `activity_id`, INDEX sur `start_ts_utc`, INDEX sur `(activity_type, start_ts_utc)` | Table centrale pour les dashboards de progression. |
| `progress_best_effort_points` | Meilleurs efforts pré-calculés par durée | `id`, `activity_id`, `start_ts_utc`, `effort_kind`, `duration_s`, `value` | 2201 lignes | PK sur `id`, UNIQUE sur `(activity_id, effort_kind, duration_s)`, INDEX sur `(effort_kind, duration_s)`, INDEX sur `(effort_kind, duration_s, start_ts_utc)` | Actuellement limité à `effort_kind='pace_s_per_km'`. |
| `progress_pace_hr_bins` | Bins Pace↔HR par activité | `id`, `activity_id`, `activity_type`, `start_ts_utc`, `pace_bin_s_per_km`, `time_s_bin`, `hr_mean_w_bpm`, `hr_q50_w_bpm` | 4820 lignes | PK sur `id`, UNIQUE sur `(activity_id, pace_bin_s_per_km)`, INDEX sur `start_ts_utc`, INDEX sur `(activity_type, start_ts_utc)`, INDEX sur `pace_bin_s_per_km` | Excellente indexation pour les requêtes de corrélation. |
| `progress_activity_tags` | Tags de classification automatique/manuel | `activity_id`, `session_tag`, `terrain_tag`, `race_marker`, `source`, `updated_at_ts` | 362 lignes | PK sur `activity_id`, INDEX sur `session_tag`, `terrain_tag`, `race_marker` | Tags auto-calculés par le progress indexer, surchargeables manuellement. |
| `progress_indexation_runs` | Log des runs d'indexation | `id`, `mode`, `strategy`, `reason`, `status`, `started_at_utc`, `finished_at_utc`, `duration_ms`, `progress_total`, `progress_done`, `result_json`, `error` | 23 lignes | PK sur `id`, INDEX sur `started_at_utc`, INDEX sur `(mode, status)` | Log technique pour debugging. |

---

## 5. Données actuellement persistées

### 5.1 Activités — métadonnées

| Donnée | Emplacement | Statut |
|---|---|---|
| ID unique (UUID) | `activities.id` + `meta.json` | ✅ Bien stocké |
| Nom | `activities.name` + `meta.json` | ✅ Double stockage (cohérent) |
| Type (real/theoretical) | `activities.activity_type` + `meta.json` | ✅ Cohérent |
| Date de début (UTC) | `activities.started_at_utc` + `meta.json` + `progress_activity_index.start_ts_utc` | ⚠️ Triple stockage, risque d'incohérence |
| Date de création (UTC) | `activities.created_at_utc` + `meta.json` | ✅ Cohérent |
| Hash SHA256 du fichier | `activities.file_hash_sha256` + `meta.json` | ✅ Clé de déduplication |
| Chemin fichier original | `activities.original_path` + disque | ✅ Cohérent |
| Chemin Parquet | `activities.parquet_path` + disque | ✅ |
| Date indexation progression | `activities.progress_indexed_at_utc` | ✅ |
| Chemin rollup progression | `activities.progress_rollup_path` | ✅ (mais usage dans le code non vérifié) |

**Redondance** : `started_at_utc` est présent dans `activities` et `progress_activity_index` (sous `start_ts_utc`). La colonne `progress_activity_index.start_ts_utc` est la source de vérité pour les endpoints de progression. La colonne `activities.started_at_utc` est déduite du fichier Parquet lors du `store()`.

### 5.2 Métriques globales (index de progression)

| Donnée | Colonne | Statut |
|---|---|---|
| Distance (m) | `progress_activity_index.distance_m` | ✅ Pré-calculé, correct |
| Temps de mouvement (s) | `progress_activity_index.moving_time_s` | ✅ |
| Temps total (s) | `progress_activity_index.elapsed_time_s` | ✅ |
| Dénivelé positif (m) | `progress_activity_index.elevation_gain_m` | ✅ |
| Allure moyenne (s/km) | `progress_activity_index.avg_pace_s_per_km` | ✅ |
| Meilleure allure (s/km) | `progress_activity_index.best_pace_s_per_km` | ✅ |
| Seuil allure (s/km) | `progress_activity_index.pace_threshold_s_per_km` | ✅ |
| FC moyenne (bpm) | `progress_activity_index.avg_hr_bpm` | ✅ |
| FC max (bpm) | `progress_activity_index.max_hr_bpm` | ✅ |
| TRIMP | `progress_activity_index.trimp` | ✅ |
| Méthode training load | `progress_activity_index.training_load_method` | ✅ |
| Dérive cardiaque (%) | `progress_activity_index.decoupling_pct` | ✅ |
| Dérive cardiaque (%) — alias | `progress_activity_index.cardiac_drift_pct` | ⚠️ Redondant avec `decoupling_pct` |
| Stabilité CV | `progress_activity_index.stability_cv` | ✅ |
| Stabilité IQR | `progress_activity_index.stability_iqr_ratio` | ✅ |
| Efficacité aérobie (m/s/bpm) | `progress_activity_index.aerobic_efficiency_m_s_per_bpm` | ✅ |
| VO2max estimé | `progress_activity_index.vo2max` | ⚠️ Présent mais souvent NULL pour activités sans capteur |
| Présence capteurs | `has_hr`, `has_power`, `has_cadence` | ✅ (booléens en INTEGER 0/1) |
| Nombre de points | `progress_activity_index.data_points` | ✅ |
| Date indexation rapide | `fast_indexation_date` | ✅ |
| Date indexation lente | `slow_indexation_date` | ✅ |

**Manque** : pas de stockage du dénivelé négatif (`elevation_loss_m`), pas de stockage de la puissance moyenne/max, pas de stockage de la cadence.

### 5.3 Séries temporelles

| Donnée | Stockage | Statut |
|---|---|---|
| Données brutes (time, lat, lon, ele, hr, speed, cadence, power, etc.) | `df.parquet` sur disque | ✅ Format Parquet, efficace en lecture |
| Séries dérivées (pace, grade, moving_mask, gap) | **Aucun** — recalculées à chaque appel | ⚠️ Coûteux pour les grandes activités |
| Séries downsamplées pour affichage | **Aucun** | ⚠️ Recalculées avec slicing à chaque appel |

### 5.4 Splits / Laps

| Donnée | Stockage | Statut |
|---|---|---|
| Splits par km | **Aucun** — `compute_splits()` à chaque appel `/activity/{id}/real` | ⚠️ Calcul coûteux sur grand DataFrame |
| Laps Garmin | **Aucun** — non supporté dans le parsing FIT actuel | ❌ Perte de données FIT |

### 5.5 Zones cardio / allure / puissance

| Donnée | Stockage | Statut |
|---|---|---|
| Zones par activité | **Aucun** — calculées dans `compute_garmin_like_stats()` via `estimate_zone_inputs()` | ⚠️ Recalcul complet à chaque `GET /activity/{id}/real` |
| Distribution par zone (% temps) | **Aucun** (sauf implicitement via `progress_pace_hr_bins`) | ⚠️ |

### 5.6 Équipements (gear)

| Donnée | Stockage | Statut |
|---|---|---|
| Équipement Garmin | **Aucun** — non importé lors de la synchro | ❌ Donnée Garmin non exploitée |

### 5.7 Imports / Fichiers sources

| Donnée | Stockage | Statut |
|---|---|---|
| Fichier original (GPX/FIT) | `data/activities/<uuid>/original.<ext>` | ✅ |
| DataFrame Parquet | `data/activities/<uuid>/df.parquet` | ✅ |
| Métadonnées JSON | `data/activities/<uuid>/meta.json` | ✅ |
| Mapping source externe | `activity_sources` (SQLite) | ✅ Uniquement pour Garmin aujourd'hui |
| Curseur synchronisation | `sync_state` (SQLite) | ✅ |

### 5.8 Caches

| Cache | Type | Utilisation |
|---|---|---|
| `MemoryCache` (LRU 32 entrées) | Mémoire, `services/cache.py` | Défini mais non utilisé par les endpoints d'analyse |
| `InMemoryCache` (256 entrées, TTL) | Mémoire, `services/cache.py` | Défini mais non utilisé par les endpoints d'analyse |
| `DiskCache` (pickle) | Disque, `services/cache.py` | Défini mais commenté "à garder désactivé sauf besoin" |
| Cache géocodage (`geo.py`) | Mémoire, TTL 24h | ✅ Actif et bien implémenté |
| Cache MFA Garmin | Mémoire, `garmin_mfa_states` | ✅ Stockage temporaire des states MFA |

**Conclusion** : l'infrastructure de cache existe mais n'est pas exploitée pour les endpoints critiques d'analyse par activité.

### 5.9 Autres

| Donnée | Emplacement | Statut |
|---|---|---|
| Objectifs de course | `goals` | ✅ Table complète et propre |
| Paramètres utilisateur | `user_settings` | ✅ Singleton bien géré |
| Traces théoriques | `traces` + `data/traces/` | ✅ Dual stockage cohérent |
| Logs d'indexation | `progress_indexation_runs` | ✅ Table technique |

---

## 6. Données calculées mais non persistées

Ce tableau couvre les principaux KPIs et données retournées par les endpoints d'analyse. La colonne "Coût estimé" évalue le coût CPU/mémoire relatif pour une activité type de 10 000 points.

| Donnée ou KPI | Endpoint concerné | Source du calcul | Coût estimé | Devrait être persisté ? | Justification |
|---|---|---|---|---|---|
| Résumé course (distance, temps, dénivelé) | `/activity/{id}/real` | `compute_basic_stats()` sur Parquet | Faible | **À discuter** | Déjà dans `progress_activity_index`. Le doubler dans une table par activité créerait une redondance. |
| Zones FC (5 zones, %temps) | `/activity/{id}/real` | `compute_garmin_like_stats()` → `estimate_zone_inputs()` | Moyen | **Oui** | Calculé à chaque consultation. Serait utile pour `/progress/series` avec agrégation par zone. |
| Zones allure (5 zones) | `/activity/{id}/real` | `compute_garmin_like_stats()` → `estimate_zone_inputs()` | Moyen | **Oui** | Idem. |
| Zones puissance (7 zones) | `/activity/{id}/real` | `compute_garmin_like_stats()` → `estimate_zone_inputs()` | Moyen | **Oui** (si power présent) | Utile pour cyclisme/triathlon. |
| Splits par km | `/activity/{id}/real` | `compute_splits()` sur Parquet | Moyen | **Oui** | Recalcul coûteux. Utile pour comparer les splits entre activités. |
| Climbs (détection montées) | `/activity/{id}/real` | `compute_climbs()` sur Parquet | Moyen-élevé | **Oui** | Détection de pics + VAM = calcul coûteux. Utile pour analyse trail. |
| Pauses (détection) | `/activity/{id}/real` | `compute_pause_markers()` | Faible | **Non** | Trivial à recalculer (filtre speed < seuil). |
| Best efforts par durée | `/activity/{id}/real` | `compute_best_efforts()` + `compute_best_efforts_by_duration()` | Élevé | **Oui** (partiellement fait) | Déjà partiellement dans `progress_best_effort_points` mais limité à `pace_s_per_km`. |
| Performance predictions (Riegel) | `/activity/{id}/real` | `compute_race_predictions()` | Faible | **Non** | Calcul trivial à partir des best efforts. |
| Pacing (moitié, drift, stabilité) | `/activity/{id}/real` | `compute_garmin_like_stats()` | Moyen | **Oui** | Déjà partiellement dans `progress_activity_index` (stability, decoupling). Manque : pace 1ère/2ème moitié. |
| Cadence (mean, max, cible) | `/activity/{id}/real` | `compute_garmin_like_stats()` | Faible | **À discuter** | Peu coûteux, mais utile pour `/progress/series`. |
| Puissance (mean, max, FTP, NP, IF, TSS) | `/activity/{id}/real` | `compute_garmin_like_stats()` | Moyen-élevé | **Oui** | Normalized Power, TSS = calculs coûteux. Utile pour cyclisme. |
| Running dynamics (stride, oscillation, GCT) | `/activity/{id}/real` | `compute_garmin_like_stats()` | Faible | **À discuter** | Données FIT uniquement, peu d'activités concernées. |
| Données carte (bbox, polyline, markers) | `/activity/{id}/map` | `calculate_bounds()` + `extract_polyline()` | Faible | **Non** | Recalcul rapide, volume élevé si persisté. |
| Series temporelles (speed, pace, HR, elev, etc.) | `/activity/{id}/series/{name}` | `SeriesRegistry.get_series_data()` | Faible (lecture Parquet) | **Non** | Le Parquet est déjà un stockage efficace. |
| Pace vs Grade bins | `/activity/{id}/pace-vs-grade` | `compute_pace_vs_grade_data()` | Élevé | **Oui** | Calcul statistique lourd (weighted quantiles, winsorization). Serait utile pour `/progress/pace-hr-waterfall`. |
| ACWR / Monotonie / Strain | `/progress/training-load` | Calculé à la volée depuis `trimp` | Moyen | **Oui** | Recalculé sur toute la période à chaque appel. Une table d'agrégation journalière réduirait le coût. |
| Heatmap calendrier | `/progress/calendar` | Agrégation depuis `progress_activity_index` | Faible-Moyen | **Non** | Requête SQL simple, 362 lignes max. |
| HR at pace / Pace at HR | `/progress/hr-at-pace`, `/progress/pace-at-hr` | Interpolation linéaire depuis `progress_pace_hr_bins` | Faible | **Non** | Données déjà pré-calculées dans `progress_pace_hr_bins`. |
| Pace-HR Waterfall | `/progress/pace-hr-waterfall` | Agrégation + regroupement depuis `progress_pace_hr_bins` | Moyen | **Non** | Données déjà dans `progress_pace_hr_bins`, calcul d'agrégation acceptable. |
| Séries agrégées (distance/semaine, etc.) | `/progress/series` | `SUM`/`AVG` sur `progress_activity_index` | Faible (362 lignes) | **Non pour l'instant** | 362 lignes = rapide. Deviendra coûteux si >10k activités. |
| FR max détecté | `/settings/personal/hr-max-detected` | `MAX(max_hr_bpm)` sur `progress_activity_index` | Faible | **Non** | Requête SQL simple. |

---

## 7. Données qui devraient être ajoutées en base

| Donnée à stocker | Niveau recommandé | Tables possibles | Bénéfice | Risque | Priorité |
|---|---|---|---|---|---|
| Zones FC/Allure/Puissance par activité | Agrégé activité | `progress_activity_zones` (nouvelle table) | Supprime le recalcul à chaque consultation de l'onglet Analyse. Permet `/progress/series` par zone. | Duplication si les seuils de zones changent (HR max, FTP). Nécessite ré-indexation si HR max mis à jour. | **P1** |
| Splits par km | Agrégé activité | `progress_activity_splits` (nouvelle table) | Accélère l'affichage des splits. Permet comparaison inter-activités. | Volume modéré (~10-40 splits/activité). | **P1** |
| Climbs (montées détectées) | Agrégé activité | `progress_activity_climbs` (nouvelle table) | Évite la détection de pics coûteuse. Utile pour analyse trail et comparaison. | Volume faible (quelques climbs/activité). | **P1** |
| Best efforts — étendre aux efforts HR/power | Agrégé activité | Étendre `progress_best_effort_points` avec `effort_kind IN ('hr_bpm', 'power_w')` | Actuellement limité à pace. Les efforts puissance/FC sont utiles pour cyclisme. | Volume : ~20 points/activité/kind, acceptable. | **P1** |
| Métriques de pacing (1ère/2ème moitié) | Agrégé activité | `progress_activity_index` (2 colonnes) | Actuellement recalculées à chaque `/activity/{id}/real`. | 2 colonnes FLOAT, risque quasi nul. | **P2** |
| Agrégations journalières/hebdomadaires | Agrégé semaine | `progress_daily_aggregates` (nouvelle table) | Accélère `/progress/series`, `/progress/training-load`, `/progress/calendar`. Évite de scanner 362+ lignes. | Risque d'incohérence si activité modifiée/supprimée. Nécessite recalcul après synchro. | **P2** |
| Puissance avancée (NP, IF, TSS) | Agrégé activité | `progress_activity_index` (3 colonnes) | Calculs coûteux faits une fois. Utile pour cyclisme. | 3 colonnes FLOAT, risque quasi nul. Données absentes si pas de puissance. | **P2** |
| Cadence moyenne/max | Agrégé activité | `progress_activity_index` (2 colonnes) | Faible coût mais utile pour `/progress/series` (suivi cadence). | 2 colonnes FLOAT. | **P3** |
| Dénivelé négatif | Agrégé activité | `progress_activity_index` (1 colonne) | Actuellement absent de l'index. Utile pour trail/descente. | 1 colonne FLOAT. | **P3** |
| Laps Garmin (depuis FIT) | Brut ou normalisé | `activity_laps` (nouvelle table) | Données présentes dans les fichiers FIT mais non extraites. Perte d'information. | Dépend du parsing FIT (non implémenté actuellement). | **P3** |
| Équipement (gear) | Normalisé | `activity_gear` (nouvelle table) | Données Garmin non importées. Utile pour suivi kilométrage chaussures/vélo. | Nécessite extraction depuis l'API Garmin + parsing. | **P4** |
| VO2max estimé (FirstBeat) | Agrégé activité | Déjà dans `progress_activity_index.vo2max` | Présent mais souvent NULL. À améliorer avec estimation locale. | Calcul complexe, dépend de la qualité des données. | **P4** |
| Running dynamics | Agrégé activité | `progress_activity_index` (colonnes) | Données FIT only, peu d'activités. Volume faible. | Faible utilité sans volume suffisant. | **P4** |

---

## 8. Données à ne pas persister

Les données suivantes **ne doivent probablement pas** être persistées en base :

| Donnée | Raison |
|---|---|
| **Coordonnées GPS brutes** (lat, lon, ele pour chaque point) | Déjà stockées efficacement dans `df.parquet`. Les dupliquer en SQLite serait redondant et volumineux. |
| **Polyline carte / bounding box** | Recalcul rapide depuis le Parquet. Le volume (centaines de points par activité) n'a pas sa place en SQLite. |
| **Markers de pause** | Trivial à recalculer (filtre `speed_m_s < 0.1`). |
| **Performance predictions (Riegel)** | Calcul simple depuis les best efforts. Les prédictions dépendent des best efforts qui peuvent changer. |
| **Séries temporelles downsamplées** | Le Parquet est déjà le format optimal. Une copie downsamplée en SQLite doublerait le stockage sans gain. |
| **Cache des réponses API complètes** | Risque élevé d'incohérence si les paramètres utilisateur (HR max, VMA, FTP) changent. Un cache HTTP (CDN/Redis) serait plus approprié. |
| **`cardiac_drift_pct` dans `progress_activity_index`** | Redondant avec `decoupling_pct` (même valeur). À supprimer ou à documenter comme alias. |
| **`progress_rollup_path` dans `activities`** | Non vérifié dans le code d'exploitation. Si inutilisé, à supprimer. |
| **Données de synchronisation anciennes** (`sync_runs` > 90 jours) | Purge périodique recommandée. Volume négligeable actuellement (18 lignes). |

---

## 9. Redondances et incohérences

### 9.1 Redondances entre tables

| Redondance | Tables concernées | Sévérité | Action recommandée |
|---|---|---|---|
| `started_at_utc` / `start_ts_utc` | `activities` ↔ `progress_activity_index` | Moyenne | `progress_activity_index.start_ts_utc` est la source de vérité pour les endpoints de progression. `activities.started_at_utc` est redondant mais utile pour le lookup rapide sans jointure. **Conserver les deux mais documenter la source canonique.** |
| `activity_type` | `activities` ↔ `progress_activity_index` ↔ `progress_pace_hr_bins` | Faible | Redondance justifiée pour éviter les jointures dans les requêtes de progression. |
| `decoupling_pct` / `cardiac_drift_pct` | `progress_activity_index` (même table) | **Forte** | Même valeur stockée deux fois. Supprimer `cardiac_drift_pct` ou le marquer comme alias. |
| `vo2max` / `vo2max_lastest` | `progress_activity_index` ↔ `user_settings` | Faible | `vo2max` = par activité, `vo2max_lastest` = dernière valeur globale. Distinction sémantique valide. |

### 9.2 Redondances de stockage

| Redondance | Description | Sévérité |
|---|---|---|
| Dual stockage activités | Une activité est stockée sur disque (`meta.json` + `original.*` + `df.parquet`) ET dans SQLite (`activities`). | Moyenne — les deux couches servent des usages différents (disque = données, SQLite = index). |
| Dual stockage traces | `traces` table + `data/traces/<uuid>/`. | Faible — même logique que pour les activités. |

### 9.3 Différences de nommage

| Concept | Nom dans le code | Nom dans l'API | Nom dans SQLite |
|---|---|---|---|
| Date de début activité | `started_at_utc` (ActivityStore) | `started_at` (ActivityMetadata) | `activities.started_at_utc`, `progress_activity_index.start_ts_utc` |
| Type d'activité | `activity_type` (ActivityStore) | `type` (ActivityLoadResponse) | `activities.activity_type` |
| Hash fichier | `file_hash` (meta.json) | `file_hash` (API) | `activities.file_hash_sha256` |
| Dérive cardiaque | `cardiac_drift_pct` (metrics.py) | `cardiac_drift_pct` (API) | `progress_activity_index.decoupling_pct` ET `cardiac_drift_pct` |
| Date indexation | `indexed_at_ts` (indexer) | N/A (non exposé) | `progress_activity_index.indexed_at_ts` |

### 9.4 Incohérences de types

| Colonne | Type déclaré (SQLAlchemy) | Type réel (SQLite) | Impact |
|---|---|---|---|
| `has_hr`, `has_power`, `has_cadence` | `Integer` | `INTEGER` | ✅ Cohérent (0/1) |
| `race_marker` | `Integer` | `INTEGER` | ✅ Cohérent |
| Tous les FLOAT | `Float` | `FLOAT` (REAL) | ✅ Cohérent |
| Tous les TEXT | `Text` / `String` | `TEXT` | ✅ Cohérent (SQLite n'a pas de VARCHAR natif) |

**Aucune incohérence de type bloquante détectée.**

### 9.5 Incohérences d'unités

Toutes les données de l'index de progression utilisent les unités SI cohérentes :
- Distances en **mètres** (`distance_m`)
- Temps en **secondes** (`moving_time_s`, `elapsed_time_s`)
- Allures en **secondes par km** (`avg_pace_s_per_km`)
- FC en **bpm** (`avg_hr_bpm`)
- Dénivelé en **mètres** (`elevation_gain_m`)
- TRIMP sans unité

**Aucune incohérence d'unité détectée.**

### 9.6 Incohérences de dates / fuseaux horaires

- Toutes les dates sont stockées en **UTC au format ISO 8601** (ex: `2026-02-09T15:23:18Z`).
- `progress_activity_index` a une colonne `local_date` et `tz` mais `tz` est souvent NULL.
- **Risque** : si `tz` n'est pas renseigné, le `local_date` peut être incorrect pour les activités proches de minuit UTC.

### 9.7 Champs calculés plusieurs fois

| Champ | Calculé dans | Doublon ? |
|---|---|---|
| `distance_m` | `compute_basic_stats()` (real analysis) + `indexer.py` (progress) | Non — l'indexer utilise `compute_basic_stats()` une fois, le résultat est stocké. L'endpoint real le recalcule si demandé. |
| `avg_hr_bpm` | `compute_garmin_like_stats()` (real analysis) + `indexer.py` (progress) | Non — même logique. |
| Zone HR | `compute_garmin_like_stats()` (real) + `estimate_zone_inputs()` (real) + potentiellement indexer | **Oui** — les zones sont recalculées à chaque appel real sans être stockées. |

---

## 10. Opportunités pour futurs KPI

Les KPI suivants seraient plus faciles à implémenter si certaines données étaient pré-calculées et stockées :

| KPI / Fonctionnalité | Données nécessaires | Faisabilité actuelle | Avec persistance |
|---|---|---|---|
| **Charge d'entraînement (CTL/ATL/TSB)** | TRIMP journalier | ✅ Déjà implémenté (`/progress/training-load`) | ✅ Déjà fonctionnel |
| **Tendance FC repos** | FC min par activité | ⚠️ Pas de FC repos stockée, seulement FC min moving | Ajouter `hr_min_bpm` (moving) et `hr_rest_bpm` (si FIT) |
| **Dérive cardiaque par zone** | FC et allure par segment | ⚠️ Calcul coûteux sur Parquet | ✅ Si zones stockées (P1) |
| **Efficacité allure/FC (aerobic efficiency)** | Déjà dans `aerobic_efficiency_m_s_per_bpm` | ✅ Disponible | ✅ Déjà stocké |
| **Évolution VO2max** | Déjà dans `vo2max` | ⚠️ Souvent NULL | Améliorer l'estimation locale |
| **Distribution par zones (global)** | Zones par activité | ❌ Recalcul coûteux | ✅ Si zones stockées (P1) |
| **Monotonie / Strain** | TRIMP journalier | ✅ Déjà implémenté | ✅ Déjà fonctionnel |
| **Progression hebdomadaire** | Agrégats semaine | ⚠️ Recalcul à chaque appel | ✅ Si agrégats pré-calculés (P2) |
| **Comparaison entre activités similaires** | Tags session + métriques | ⚠️ Jointure tags + index fonctionnelle | ✅ Fonctionnel via `/progress/activities` |
| **Segmentation montée/descente/plat** | Grade par segment | ⚠️ Calcul coûteux | ✅ Si climbs stockés (P1) |
| **Puissance normalisée (NP)** | Série puissance | ❌ Calcul coûteux sur Parquet | ✅ Si NP stockée (P2) |
| **Score de régularité (pacing)** | Déjà dans `stability_cv` et `stability_iqr_ratio` | ✅ Disponible | ✅ Déjà stocké |
| **Heatmap des intensités** | Distribution pace/FC par activité | ⚠️ Partiellement via `progress_pace_hr_bins` | ✅ Déjà partiellement fonctionnel |
| **Détection des séances structurées** | Tags `session_tag` | ✅ Déjà fait (auto-classification) | ✅ Déjà fonctionnel |
| **Suivi kilométrage équipement** | Gear + distance | ❌ Gear non importé | P4 |
| **Prédiction course** | Riegel depuis best efforts | ✅ Déjà fait en temps réel | ✅ Déjà fonctionnel |
| **Score colline (hill score)** | Climbs + VAM | ❌ Climbs recalculés | ✅ Si climbs stockés (P1) |
| **Endurance score** | Données multi-activités | ❌ Complexe | P4 |
| **Charge chronique vs aiguë (ACWR)** | TRIMP 7j et 42j | ✅ Déjà implémenté | ✅ Déjà fonctionnel |

---

## 11. Recommandations techniques

### Court terme (faible risque, gains rapides)

1. **Supprimer la colonne `cardiac_drift_pct` ou la marquer comme alias de `decoupling_pct`** dans `progress_activity_index`. Les deux colonnes contiennent la même valeur. Garder `decoupling_pct` comme nom canonique.

2. **Ajouter un index sur `progress_activity_index.activity_type` seul** pour les requêtes filtrant uniquement par type (sans plage de dates).

3. **Documenter les ~30 endpoints manquants** dans `docs/metrics_catalog.md` (traces, settings, goals, geo, garmin, CRUD activities, progress/index, progress/training-load, progress/calendar). Ne pas le faire maintenant sans demande explicite — c'est noté dans ce rapport.

4. **Ajouter un cache LRU pour `/activity/{id}/real`** : le résultat de `analyze_real_activity()` pourrait être caché en mémoire avec une TTL de 60 secondes et invalidé si les paramètres utilisateur (HR max) changent.

5. **Activer le `InMemoryCache` existant** pour les réponses `/activity/{id}/real` et `/activity/{id}/pace-vs-grade` avec une TTL courte (30-60s).

### Moyen terme (évolution de schéma légère)

6. **Créer `progress_activity_zones`** : stocker les zones HR/pace/power par activité (P1). Schéma proposé :
   ```sql
   CREATE TABLE progress_activity_zones (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       activity_id TEXT NOT NULL,
       zone_type TEXT NOT NULL,  -- 'heart_rate', 'pace', 'power'
       zone_name TEXT NOT NULL,  -- 'Z1', 'Z2', ...
       range_low REAL,
       range_high REAL,
       time_s REAL NOT NULL,
       time_pct REAL NOT NULL,
       FOREIGN KEY (activity_id) REFERENCES activities(id)
   );
   CREATE INDEX ix_zones_activity ON progress_activity_zones(activity_id, zone_type);
   ```

7. **Créer `progress_activity_splits`** : stocker les splits par km (P1).

8. **Créer `progress_activity_climbs`** : stocker les montées détectées (P1).

9. **Étendre `progress_best_effort_points`** à `effort_kind IN ('hr_bpm', 'power_w')` (P1).

10. **Ajouter `elevation_loss_m`, `cadence_mean_spm`, `cadence_max_spm`, `power_mean_w`, `power_max_w`** à `progress_activity_index` (P2-P3).

11. **Créer `progress_daily_aggregates`** pour les agrégations journalières (P2). Schéma proposé :
    ```sql
    CREATE TABLE progress_daily_aggregates (
        date_utc TEXT PRIMARY KEY,
        distance_m REAL,
        moving_time_s REAL,
        elapsed_time_s REAL,
        elevation_gain_m REAL,
        trimp REAL,
        activity_count INTEGER,
        computed_at_utc TEXT NOT NULL
    );
    ```

### Long terme (refonte partielle)

12. **Pipeline d'agrégation automatique** : après chaque indexation lente, calculer les agrégations hebdomadaires/mensuelles et les stocker. Invalider lors de l'ajout/suppression d'activités.

13. **Cache API structuré** : implémenter un cache Redis (ou SQLite) pour les réponses d'analyse par activité, avec invalidation lors du changement des paramètres utilisateur (VMA, HR max, FTP).

14. **Normalisation des noms de colonnes** : unifier `started_at_utc` vs `start_ts_utc`, `created_at_utc` vs `created_at`. Adopter un suffixe `_utc` systématique.

15. **Extraction des données FIT avancées** : laps, gear, running dynamics, développante de puissance. Ajouter les tables correspondantes (P3-P4).

16. **Purge automatique des données anciennes** : `sync_runs` > 90 jours, `progress_indexation_runs` > 30 jours (configurable).

---

## 12. Index SQLite recommandés

| Table | Colonnes | Endpoint(s) accéléré(s) | Justification | Priorité |
|---|---|---|---|---|
| `progress_activity_index` | `activity_type` | `/progress/activities?type=real`, `/progress/series?type=real` | Les filtres par type sont fréquents. L'index composite `(activity_type, start_ts_utc)` couvre partiellement ce besoin mais un index simple sur `activity_type` serait plus efficace pour les requêtes sans plage de dates. | **P3** |
| `progress_activity_index` | `local_date` | `/progress/calendar` | La heatmap calendrier filtre par année (via `start_ts_utc`). L'index actuel sur `start_ts_utc` est suffisant. | — (déjà couvert) |
| `progress_best_effort_points` | `activity_id` | Jointures avec `progress_activity_index` | Pas d'index simple sur `activity_id` seul (seulement dans les contraintes uniques et composites). Utile pour les jointures. | **P3** |
| `progress_pace_hr_bins` | `activity_id` | Jointures avec `progress_activity_tags` | L'index unique `(activity_id, pace_bin)` couvre déjà. | — (déjà couvert) |
| `progress_activity_tags` | `source` | Filtrage par source de tag (auto vs manual) | Pas d'index actuel. Utile pour `GET /progress/session-taxonomy?source=manual`. | **P3** |
| `activity_sources` | `activity_id` | Lookup inverse (source → activité) | Pas d'index sur `activity_id` seul. La FK sur `activities(id)` ne crée pas automatiquement d'index en SQLite. | **P2** |

**Note** : les index existants couvrent déjà bien les cas d'usage principaux. Les recommandations ci-dessus sont des optimisations marginales pour des cas spécifiques.

---

## 13. Risques et points de vigilance

### 13.1 Risque de cache obsolète

- Si un cache est ajouté pour `/activity/{id}/real`, il faut l'invalider quand `user_settings.hr_max_source` ou `user_settings.hr_max_manual_bpm` change (les zones et métriques dépendent du HR max).
- Le cache géocodage (`geo.py`) a un TTL de 24h, ce qui est raisonnable pour des noms de villes.

### 13.2 Risque de duplication de vérité métier

- La **double persistance** (fichier + SQLite) pour les activités implique que `activities.started_at_utc` pourrait diverger de `progress_activity_index.start_ts_utc`. Actuellement, les deux sont calculés à partir du même DataFrame Parquet, donc le risque est faible. Mais si l'un est mis à jour sans l'autre, une divergence apparaîtra.
- La colonne `decoupling_pct` et `cardiac_drift_pct` dans `progress_activity_index` contiennent la même valeur. Si un jour elles divergent, laquelle est la source de vérité ?

### 13.3 Risque de migration difficile

- Les migrations SQLite sont faites "à la main" dans `db/session.py` via `ALTER TABLE ADD COLUMN`. C'est fragile mais fonctionnel pour des ajouts de colonnes.
- **Pas de gestion de version de schéma** : impossible de savoir quelle version de schéma est déployée sans inspecter les colonnes.
- Ajouter des tables avec contraintes FOREIGN KEY nécessite `PRAGMA foreign_keys=ON` (activé par défaut dans SQLAlchemy ? À vérifier).

### 13.4 Risque de gonflement excessif de la base

- La base actuelle fait probablement quelques Mo (362 activités). Si CourseScope atteint 10 000 activités :
  - `progress_pace_hr_bins` : ~130 000 lignes (13 bins/activité en moyenne actuellement) → acceptable.
  - `progress_best_effort_points` : ~60 000 lignes → acceptable.
  - L'ajout de `progress_activity_zones` ajouterait ~50 000 lignes pour 10 000 activités → acceptable.
- **Le vrai volume est sur le système de fichiers** : chaque `df.parquet` peut faire plusieurs Mo. Pour 10 000 activités, le stockage disque serait le facteur limitant, pas SQLite.

### 13.5 Risque de ralentissement à l'import

- L'import d'une activité (`POST /activity/load`) déclenche :
  1. Écriture du fichier original
  2. Écriture du Parquet
  3. Écriture du `meta.json`
  4. INSERT dans `activities`
  5. **Indexation de progression complète** (`fast_indexation` et potentiellement `slow_indexation`)
  
  L'indexation lente est asynchrone (background), mais l'indexation rapide est synchrone et bloquante. Pour de très gros fichiers (>50 000 points), cela pourrait ralentir l'upload.

### 13.6 Risque de divergence entre données brutes et données agrégées

- Si le `df.parquet` est regénéré ou modifié (ce qui n'arrive pas actuellement), l'index de progression (`progress_activity_index`) ne serait pas automatiquement mis à jour. La vérification `/progress/verify` détecterait la divergence mais ne la corrigerait pas automatiquement.

---

## 14. Plan d'action recommandé

| Étape | Action | Impact | Risque | Priorité |
|---|---|---|---|---|
| 1 | Supprimer ou marquer `cardiac_drift_pct` comme alias de `decoupling_pct` | 🟢 Faible | 🟢 Très faible | **P1** |
| 2 | Créer `progress_activity_zones` (HR, pace, power) et peupler via indexation lente | 🟡 Moyen | 🟢 Faible | **P1** |
| 3 | Créer `progress_activity_splits` et peupler via indexation lente | 🟡 Moyen | 🟢 Faible | **P1** |
| 4 | Créer `progress_activity_climbs` et peupler via indexation lente | 🟡 Moyen | 🟢 Faible | **P1** |
| 5 | Étendre `progress_best_effort_points` aux efforts HR et power | 🟡 Moyen | 🟢 Faible | **P1** |
| 6 | Activer le cache `InMemoryCache` pour `/activity/{id}/real` (TTL 60s) | 🟢 Faible | 🟡 Moyen (cache invalidation) | **P2** |
| 7 | Ajouter colonnes manquantes à `progress_activity_index` (`elevation_loss_m`, pacing, puissance, cadence) | 🟡 Moyen | 🟢 Faible | **P2** |
| 8 | Créer `progress_daily_aggregates` pour `/progress/series` et `/progress/training-load` | 🟡 Moyen | 🟡 Moyen (recalcul après modif) | **P2** |
| 9 | Ajouter index sur `activity_sources.activity_id` | 🟢 Faible | 🟢 Très faible | **P2** |
| 10 | Documenter les endpoints manquants dans `docs/metrics_catalog.md` | 🟢 Faible | 🟢 Nul | **P3** |
| 11 | Ajouter index sur `progress_activity_index.activity_type` seul | 🟢 Faible | 🟢 Très faible | **P3** |
| 12 | Ajouter index sur `progress_activity_tags.source` | 🟢 Faible | 🟢 Très faible | **P3** |
| 13 | Implémenter extraction des laps Garmin depuis FIT | 🟡 Moyen | 🟡 Moyen (parsing complexe) | **P3** |
| 14 | Pipeline d'agrégation automatique post-indexation | 🔴 Élevé | 🟡 Moyen | **P4** |
| 15 | Cache API distribué (Redis) | 🔴 Élevé | 🟡 Moyen | **P4** |
| 16 | Normalisation des noms de colonnes (`_utc` systématique) | 🔴 Élevé | 🔴 Élevé (casse tout) | **P4** |
| 17 | Extraction gear Garmin + suivi kilométrage | 🟡 Moyen | 🟡 Moyen | **P4** |

---

## 15. Conclusion

### Ce que la base SQLite fait déjà correctement

- ✅ **Déduplication** efficace via `file_hash_sha256` (SHA256 du fichier original).
- ✅ **Index de progression** (`progress_activity_index`) bien conçu avec 30+ métriques pré-calculées, couvrant distance, temps, FC, TRIMP, stabilité, dérive cardiaque, efficacité aérobie.
- ✅ **Bins Pace↔HR** (`progress_pace_hr_bins`) parfaitement indexés pour les requêtes de corrélation multi-activités.
- ✅ **Tags de classification** automatiques (session, terrain, race) avec possibilité de surcharge manuelle.
- ✅ **Traces théoriques** avec déduplication par `route_fingerprint` (SHA256 des coordonnées simplifiées).
- ✅ **Indexation** exhaustive et bien couverte (15 index explicites + contraintes UNIQUE et PK).
- ✅ **Cohérence des unités** : tout en SI (mètres, secondes, bpm).

### Ce qui manque réellement

- ❌ **Persistance des analyses par activité** : zones (HR/pace/power), splits, climbs, best efforts étendus (HR/power), puissance avancée (NP, IF, TSS). Tout est recalculé à chaque consultation.
- ❌ **Agrégations temporelles pré-calculées** : `/progress/series` et `/progress/training-load` scannent toute la table `progress_activity_index` à chaque appel.
- ❌ **Cache API pour les endpoints d'analyse** : l'infrastructure existe (`InMemoryCache`, `MemoryCache`) mais n'est pas utilisée.
- ❌ **Documentation API incomplète** : ~30 endpoints (sur 39) non documentés dans `docs/metrics_catalog.md`.
- ❌ **Données Garmin non exploitées** : laps, gear, running dynamics avancés.

### Ce qui serait prématuré

- 🔮 Cache distribué (Redis) : 362 activités ne justifient pas cette complexité.
- 🔮 Refonte du modèle de données : la structure actuelle est saine et extensible.
- 🔮 Normalisation des noms de colonnes : trop de code dépendant, risque de régression élevé pour un gain faible.
- 🔮 Extraction gear Garmin : dépend de l'API Garmin, complexité élevée, gain utilisateur limité actuellement.

### Quelles évolutions sont les plus rentables

1. **P1 — Zones, splits, climbs** : persister ces données dans des tables dédiées. Gain immédiat sur les performances de l'onglet Analyse (évite le rechargement complet du Parquet + recalcul pour chaque consultation). Coût d'implémentation modéré (3 tables + modification de l'indexer).

2. **P2 — Agrégations journalières** : une table `progress_daily_aggregates` réduirait le temps de réponse de `/progress/training-load` et `/progress/series` de O(n) à O(1). Particulièrement important si le nombre d'activités dépasse 1000.

3. **P2 — Cache LRU pour `/activity/{id}/real`** : activation de l'infrastructure de cache existante. Gain immédiat, risque faible si TTL courte et invalidation lors du changement de HR max.

---

*Rapport généré le 30 juin 2026. Aucune modification applicative n'a été effectuée. Base SQLite non modifiée. Fichier temporaire d'audit supprimé.*
