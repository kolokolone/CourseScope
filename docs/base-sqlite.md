# Base SQLite — Référence technique

> **Type** : Référence technique · **Base** : `data/coursescope.sqlite`
> **Dernière mise à jour** : 2026-06-30

## Objectif

Ce document décrit la structure, le fonctionnement et les conventions de la base SQLite de CourseScope. Il s'adresse aux développeurs et agents qui implémentent ou modifient des fonctionnalités liées au stockage relationnel.

## Périmètre

**Couvert** : schéma des 16 tables, ORM SQLAlchemy, cycle de vie des données, mécanismes de migration, conventions de nommage, accès aux données via les repositories.

**Non couvert** : le stockage fichier (`data/activities/`, `data/traces/`), l'architecture d'indexation (voir `docs/indexation.md`) et les contrats API (voir `docs/metrics_catalog.md` et `docs/race-planning.md`).

---

## 1. Vue d'ensemble

### 1.1 Emplacement et configuration

| Élément | Valeur |
|---|---|
| Fichier | `data/coursescope.sqlite` |
| Fichiers auxiliaires | `coursescope.sqlite-wal`, `coursescope.sqlite-shm` (Write-Ahead Log) |
| URL de connexion | `sqlite:///<data_dir>/coursescope.sqlite` ou variable `COURSESCOPE_DATABASE_URL` |
| Initialisation | `backend/db/session.py` → `init_db()` au démarrage FastAPI |

La base est créée automatiquement au premier lancement via `Base.metadata.create_all()`. Le mode WAL est activé pour supporter les lectures concurrentes avec le `TestClient` FastAPI (`check_same_thread=False`).

### 1.2 Architecture double stockage

CourseScope utilise **deux couches de persistance** pour les activités :

```
┌─────────────────────────────────────────────────────┐
│  SQLite (data/coursescope.sqlite)                   │
│  - Index de déduplication (activities)              │
│  - Index analytique (progress_activity_index + ...)  │
│  - Configuration (user_settings)                    │
│  - Synchronisation (sync_state, sync_runs)          │
│  - Traces & objectifs (traces, goals)               │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│  Système de fichiers (data/activities/<uuid>/)      │
│  - Fichier original (original.gpx / original.fit)   │
│  - DataFrame Parquet (df.parquet)                   │
│  - Métadonnées JSON (meta.json)                     │
└─────────────────────────────────────────────────────┘
```

SQLite fait office d'**index** et de **cache analytique**. Les données brutes (coordonnées GPS, séries temporelles) restent en Parquet, format optimisé pour la lecture colonne par colonne.

### 1.3 Technologies

| Couche | Technologie | Fichier principal |
|---|---|---|
| ORM | SQLAlchemy 2.x (DeclarativeBase) | `backend/db/models.py` |
| Session | `sessionmaker` avec `autoflush=False` | `backend/db/session.py` |
| Migrations | Manuelles dans `init_db()` | `backend/db/session.py` (lignes 43-94) |
| Requêtes | SQLAlchemy Core (`select`, `delete`) | `backend/db/*_repository.py` |

---

## 2. Schéma des tables

### 2.1 `activities` — Registre des activités

Rôle : index de déduplication et métadonnées essentielles. Une ligne par activité importée.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | TEXT(36) | PK | UUID v4 |
| `name` | TEXT | NULL | Nom affiché (peut être NULL) |
| `activity_type` | TEXT(32) | NOT NULL | `real` pour les imports actifs ; d'anciennes bases peuvent encore contenir `theoretical` |
| `started_at_utc` | TEXT | NULL | Date de début inférée du fichier, format ISO 8601 UTC |
| `created_at_utc` | TEXT | NOT NULL | Date d'import, format ISO 8601 UTC |
| `file_hash_sha256` | TEXT(64) | UNIQUE, NOT NULL | SHA256 du fichier original (clé de déduplication) |
| `original_path` | TEXT | NOT NULL | Chemin absolu du fichier original sur disque |
| `parquet_path` | TEXT | NOT NULL | Chemin absolu du `df.parquet` |
| `progress_indexed_at_utc` | TEXT | NULL | Dernière indexation réussie (ajouté par migration) |
| `progress_rollup_path` | TEXT | NULL | Chemin du rollup de progression (ajouté par migration) |

**Index** : PK sur `id`, UNIQUE sur `file_hash_sha256`.

**Repository** : `backend/db/repository.py` → `ActivityIndexRepository`.

**Cycle de vie** :
1. Créé par `LocalTempStorage.store()` après écriture du fichier et du Parquet.
2. Lu par `ActivityIndexRepository.get_activity_id_by_hash()` pour la déduplication.
3. Peut être supprimé par `DELETE /activities` (vidage complet).

### 2.2 `activity_sources` — Mapping source externe

Rôle : lier une activité CourseScope à son identifiant dans un système externe (Garmin Connect).

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | Identifiant technique |
| `activity_id` | TEXT(36) | FK → `activities.id`, NOT NULL | Activité CourseScope |
| `source` | TEXT(32) | NOT NULL | Nom de la source (`garmin`) |
| `source_activity_id` | TEXT | NOT NULL | Identifiant dans le système externe |

**Index** : PK sur `id`, UNIQUE sur `(source, source_activity_id)`. Pas d'index sur `activity_id` seul — à considérer pour les lookups inverses.

**Repository** : `backend/db/repository.py` → `ActivityIndexRepository`.

### 2.3 `traces` — Parcours théoriques

Rôle : stocker les parcours sauvegardés pour l'analyse théorique.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | TEXT(36) | PK | UUID v4 |
| `name` | TEXT | NULL | Nom du parcours |
| `created_at_utc` | TEXT | NOT NULL | Date de création |
| `file_hash_sha256` | TEXT(64) | UNIQUE, NOT NULL | SHA256 du fichier GPX/FIT |
| `route_fingerprint` | TEXT(64) | NULL | SHA256 des coordonnées simplifiées (déduplication géométrique) |
| `distance_km` | REAL | NOT NULL, DEFAULT 0 | Distance en km |
| `elevation_gain_m` | REAL | NOT NULL, DEFAULT 0 | Dénivelé positif en m |
| `elevation_loss_m` | REAL | NULL | Dénivelé négatif en m |
| `elevation_min_m` | REAL | NULL | Altitude min en m |
| `elevation_max_m` | REAL | NULL | Altitude max en m |
| `original_filename` | TEXT | NULL | Nom du fichier d'origine |
| `original_path` | TEXT | NOT NULL | Chemin du fichier sauvegardé |
| `parquet_path` | TEXT | NULL | Chemin du DataFrame canonique Parquet |
| `parquet_source_hash_sha256` | TEXT(64) | NULL | Empreinte du fichier utilisé pour produire le Parquet |
| `dataframe_schema_version` | TEXT(32) | NULL | Version du contrat du DataFrame |
| `parquet_generated_at_utc` | TEXT | NULL | Date ISO UTC de génération du Parquet |

**Index** : PK sur `id`, UNIQUE sur `file_hash_sha256`, INDEX sur `route_fingerprint`.

**Repository** : `backend/db/trace_repository.py` → `TraceRepository`.

**Déduplication** : deux niveaux — par hash de fichier (binaire) et par empreinte de parcours (géométrique). L'empreinte est calculée par `storage/trace_store.py` → `compute_route_fingerprint()`.

### 2.3.1 Tables de préparation de course

Les objets principaux ne sont pas stockés dans un bloc de métadonnées. Ils utilisent des tables relationnelles avec suppression en cascade depuis la trace.

| Table | Parent | Contenu principal |
|---|---|---|
| `race_plans` | `traces.id` | nom, `goal_id`, date, départ, fuseau, scénario actif, paramètres communs, notes, timestamps |
| `race_scenarios` | `race_plans.id` | objectif, valeur canonique, Minetti, VMA, calibration, météo, statut actif, timestamps |
| `race_stops` | `race_scenarios.id` | distance en km, type, durée en secondes, notes, ordre |
| `race_strategy_segments` | `race_scenarios.id` | début/fin en km, cible d'allure, notes, ordre |
| `race_nutrition_items` | `race_scenarios.id` | distance en km, nutrition/hydratation, quantité, notes, ordre |
| `race_equipment_items` | `race_plans.id` | libellé, état de checklist, notes, ordre |
| `race_course_points` | `race_plans.id` | point remarquable ou segment personnalisé, distances, notes, ordre |

Tous les identifiants sont des UUID v4 sur 36 caractères. Les paramètres extensibles utilisent uniquement les colonnes JSON sérialisées explicitement prévues (`common_parameters_json`, paramètres personnels, calibration et météo). Les résultats de calcul ne sont pas persistés comme source de vérité.

### 2.4 `goals` — Objectifs de course

Rôle : objectifs de course avec cibles de temps ou d'allure.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | TEXT(36) | PK | UUID v4 |
| `name` | TEXT | NOT NULL | Nom de l'objectif |
| `event_date` | TEXT | NOT NULL | Date de l'événement (YYYY-MM-DD) |
| `distance_km` | REAL | NOT NULL | Distance en km |
| `location` | TEXT | NULL | Description libre du lieu |
| `location_city` | TEXT | NULL | Ville (ajouté par migration) |
| `location_country` | TEXT | NULL | Pays (ajouté par migration) |
| `location_country_code` | TEXT(8) | NULL | Code pays ISO (ajouté par migration) |
| `location_lat` | REAL | NULL | Latitude (ajouté par migration) |
| `location_lon` | REAL | NULL | Longitude (ajouté par migration) |
| `target_time_s` | REAL | NULL | Temps cible en secondes (exclusif avec target_pace) |
| `target_pace_s_per_km` | REAL | NULL | Allure cible en s/km (exclusif avec target_time) |
| `race_type` | TEXT(16) | NOT NULL, DEFAULT `road` | Type de course (`road`, `trail`) |
| `notes` | TEXT | NULL | Notes libres |
| `created_at_utc` | TEXT | NOT NULL | Date de création |
| `updated_at_utc` | TEXT | NOT NULL | Date de dernière modification |

**Index** : PK sur `id`, INDEX sur `event_date`.

**Repository** : `backend/db/goals_repository.py` → `GoalsRepository`.

**Règle métier** : `target_time_s` et `target_pace_s_per_km` sont mutuellement exclusifs. L'API impose exactement l'un des deux.

### 2.5 `user_settings` — Configuration personnelle

Rôle : singleton (id=1) contenant les paramètres utilisateur influençant les calculs.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | INTEGER | PK | Toujours 1 |
| `vma_kmh` | REAL | NULL | VMA en km/h |
| `vo2max_lastest` | REAL | NULL | Dernière valeur VO2max connue (ajouté par migration) |
| `hr_max_manual_bpm` | INTEGER | NULL | FC max manuelle |
| `hr_max_source` | TEXT(16) | NOT NULL, DEFAULT `detected` | Source FC max : `detected` ou `manual` |
| `updated_at_utc` | TEXT | NOT NULL | Date de dernière modification |

**Index** : PK sur `id`.

**Repository** : `backend/db/settings_repository.py` → `SettingsRepository`.

**FC max effective** : si `hr_max_source = 'detected'`, la FC max est `MAX(max_hr_bpm)` sur `progress_activity_index`. Sinon, c'est `hr_max_manual_bpm`. La détection est faite à chaque appel `get_detected_hr_max()`.

### 2.6 `sync_state` — Curseur de synchronisation

Rôle : mémoriser le dernier curseur de synchronisation par source externe.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `source` | TEXT(32) | PK | Nom de la source (`garmin`) |
| `cursor_time_utc` | TEXT | NULL | Dernier timestamp synchronisé |
| `updated_at_utc` | TEXT | NOT NULL | Date de mise à jour |

**Index** : PK sur `source`.

### 2.7 `sync_runs` — Historique des synchronisations

Rôle : journal des exécutions de synchronisation.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | TEXT(36) | PK | UUID v4 |
| `source` | TEXT(32) | NOT NULL | Source (`garmin`) |
| `started_at_utc` | TEXT | NOT NULL | Début du run |
| `finished_at_utc` | TEXT | NULL | Fin du run |
| `status` | TEXT(16) | NOT NULL | `running`, `ok`, `error` |
| `imported_count` | INTEGER | NOT NULL, DEFAULT 0 | Nombre d'activités importées |
| `skipped_count` | INTEGER | NOT NULL, DEFAULT 0 | Nombre d'activités ignorées (doublons) |
| `error` | TEXT | NULL | Message d'erreur |

**Index** : PK sur `id`.

---

### 2.8 Tables de progression (préfixe `progress_`)

Ces tables constituent l'**index analytique**. Elles sont peuplées par le système d'indexation fast/slow (voir `docs/indexation.md`).

#### 2.8.1 `progress_activity_index` — Métriques agrégées par activité

Table centrale des dashboards de progression. Une ligne par activité, 31 colonnes.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `activity_id` | TEXT(36) | PK | Référence vers `activities.id` |
| `activity_type` | TEXT(32) | NOT NULL | `real` pour les nouvelles activités ; `theoretical` peut subsister dans un index historique |
| `start_ts_utc` | TEXT | NOT NULL | Date de début UTC |
| `local_date` | TEXT | NULL | Date locale (YYYY-MM-DD) |
| `tz` | TEXT | NULL | Fuseau horaire IANA |
| `fingerprint` | TEXT | NOT NULL | Empreinte de l'activité (hash du fichier + taille Parquet) |
| `metrics_version` | INTEGER | NOT NULL | Version du calcul des métriques (actuellement 7) |
| `indexed_at_ts` | TEXT | NOT NULL | Date d'indexation |
| `fast_indexation_date` | TEXT | NULL | Date dernière indexation rapide (ajouté par migration) |
| `slow_indexation_date` | TEXT | NULL | Date dernière indexation lente (ajouté par migration) |
| **Métriques de base** ||||
| `distance_m` | REAL | NULL | Distance en mètres |
| `moving_time_s` | REAL | NULL | Temps de mouvement en secondes |
| `elapsed_time_s` | REAL | NULL | Temps total en secondes |
| `elevation_gain_m` | REAL | NULL | Dénivelé positif en mètres |
| **Allure** ||||
| `avg_pace_s_per_km` | REAL | NULL | Allure moyenne en s/km |
| `best_pace_s_per_km` | REAL | NULL | Meilleure allure en s/km |
| `pace_threshold_s_per_km` | REAL | NULL | Allure seuil estimée |
| **Cardio** ||||
| `avg_hr_bpm` | REAL | NULL | FC moyenne en bpm |
| `max_hr_bpm` | REAL | NULL | FC max en bpm |
| **Charge** ||||
| `trimp` | REAL | NULL | Training Impulse (Edwards) |
| `training_load_method` | TEXT | NULL | Méthode de calcul (`edwards`) |
| **Dérive & Stabilité** ||||
| `decoupling_pct` | REAL | NULL | Dérive cardiaque en % (écart FC 1ère vs 2ème moitié) |
| `cardiac_drift_pct` | REAL | NULL | **Alias de `decoupling_pct`** (redondance connue) |
| `stability_cv` | REAL | NULL | Coefficient de variation de l'allure |
| `stability_iqr_ratio` | REAL | NULL | Ratio IQR de l'allure |
| **Efficacité** ||||
| `aerobic_efficiency_m_s_per_bpm` | REAL | NULL | Efficacité aérobie (vitesse / FC) |
| `vo2max` | REAL | NULL | VO2max estimé (ajouté par migration) |
| **Capteurs** ||||
| `has_hr` | INTEGER | NOT NULL, DEFAULT 0 | Capteur FC présent (0/1) |
| `has_power` | INTEGER | NOT NULL, DEFAULT 0 | Capteur puissance présent (0/1) |
| `has_cadence` | INTEGER | NOT NULL, DEFAULT 0 | Capteur cadence présent (0/1) |
| `data_points` | INTEGER | NULL | Nombre de points dans le Parquet |
| **Métriques ajoutées P2** ||||
| `elevation_loss_m` | REAL | NULL | Dénivelé négatif en mètres |
| `pace_first_half_s_per_km` | REAL | NULL | Allure première moitié |
| `pace_second_half_s_per_km` | REAL | NULL | Allure seconde moitié |
| `power_normalized_w` | REAL | NULL | Normalized Power en watts |
| `power_intensity_factor` | REAL | NULL | Intensity Factor |
| `power_tss` | REAL | NULL | Training Stress Score |
| `cadence_mean_spm` | REAL | NULL | Cadence moyenne |
| `cadence_max_spm` | REAL | NULL | Cadence maximale |

**Index** : PK sur `activity_id`, INDEX sur `start_ts_utc`, INDEX composite sur `(activity_type, start_ts_utc)`.

**Repository** : `backend/db/progress_repository.py` → `ProgressRepository`.

**Mécanisme de mise à jour** : l'indexation lente recalcule les métriques via `compute_basic_stats()` et `compute_garmin_like_stats()` appliqués au DataFrame Parquet. La colonne `fingerprint` détecte si le Parquet a changé et nécessite un recalcul.

#### 2.8.2 `progress_best_effort_points` — Meilleurs efforts

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | |
| `activity_id` | TEXT(36) | NOT NULL | Activité |
| `start_ts_utc` | TEXT | NOT NULL | Date de l'activité |
| `effort_kind` | TEXT(64) | NOT NULL | Type d'effort (`pace_s_per_km`, `hr_bpm`, `power_w`) |
| `duration_s` | INTEGER | NOT NULL | Durée de l'effort en secondes |
| `value` | REAL | NOT NULL | Valeur (allure en s/km pour pace) |

**Index** : PK sur `id`, UNIQUE sur `(activity_id, effort_kind, duration_s)`, INDEX sur `(effort_kind, duration_s)`, INDEX sur `(effort_kind, duration_s, start_ts_utc)`.

**Contenu** : les meilleurs efforts sont extraits pour `pace_s_per_km`, `hr_bpm` et `power_w` sur des durées de 30s à 3600s. Les efforts FC et puissance sont désormais supportés en complément de l'allure.

#### 2.8.3 `progress_pace_hr_bins` — Bins Pace ↔ Fréquence Cardiaque

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | |
| `activity_id` | TEXT(36) | NOT NULL | Activité |
| `activity_type` | TEXT(32) | NOT NULL | `real` pour les nouvelles activités ; valeur historique conservée si déjà indexée |
| `start_ts_utc` | TEXT | NOT NULL | Date de l'activité |
| `pace_bin_s_per_km` | REAL | NOT NULL | Centre du bin d'allure (s/km) |
| `time_s_bin` | REAL | NOT NULL | Temps passé dans le bin |
| `hr_mean_w_bpm` | REAL | NULL | FC moyenne pondérée par le temps |
| `hr_q50_w_bpm` | REAL | NULL | FC médiane pondérée |

**Index** : PK sur `id`, UNIQUE sur `(activity_id, pace_bin_s_per_km)`, INDEX sur `start_ts_utc`, INDEX sur `(activity_type, start_ts_utc)`, INDEX sur `pace_bin_s_per_km`.

**Utilisation** : alimente `/progress/hr-at-pace`, `/progress/pace-at-hr` et `/progress/pace-hr-waterfall`. Le `hr_q50_w_bpm` est préféré au `hr_mean_w_bpm` car plus robuste aux outliers.

#### 2.8.4 `progress_activity_tags` — Classification automatique

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `activity_id` | TEXT(36) | PK | Activité |
| `session_tag` | TEXT(32) | NULL | Type de séance : `easy`, `tempo`, `interval`, `long_run`, `unknown` |
| `terrain_tag` | TEXT(32) | NULL | Type de terrain : `flat`, `rolling`, `hilly`, `unknown` |
| `race_marker` | INTEGER | NOT NULL, DEFAULT 0 | Course/compétition (0/1) |
| `source` | TEXT(16) | NOT NULL, DEFAULT `auto` | Origine : `auto` (classification) ou `manual` (utilisateur) |
| `updated_at_ts` | TEXT | NOT NULL | Date de dernière modification |

**Index** : PK sur `activity_id`, INDEX sur `session_tag`, `terrain_tag`, `race_marker`.

**Classification automatique** : effectuée par `progress/indexer.py` → `_classify_session_and_terrain()` selon des seuils sur l'allure, la FC et la stabilité. Les tags manuels (`POST /progress/tags`) ne sont pas écrasés par l'auto-classification (`preserve_manual=True`).

#### 2.8.5 `progress_indexation_runs` — Journal d'indexation

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | TEXT(36) | PK | UUID v4 |
| `mode` | TEXT(16) | NOT NULL | `fast` ou `slow` |
| `strategy` | TEXT(32) | NULL | Stratégie slow : `incremental`, `backfill_missing`, `backfill_full` |
| `reason` | TEXT | NULL | Déclencheur (ex: `garmin_sync`, `progress_page`) |
| `status` | TEXT(16) | NOT NULL | `running`, `completed`, `error` |
| `started_at_utc` | TEXT | NOT NULL | Début du run |
| `finished_at_utc` | TEXT | NULL | Fin du run |
| `duration_ms` | INTEGER | NOT NULL, DEFAULT 0 | Durée en millisecondes |
| `progress_total` | INTEGER | NOT NULL, DEFAULT 0 | Nombre total d'activités à traiter |
| `progress_done` | INTEGER | NOT NULL, DEFAULT 0 | Nombre d'activités traitées |
| `result_json` | TEXT | NULL | Résultat JSON (scanned, indexed, errors...) |
| `error` | TEXT | NULL | Message d'erreur |

**Index** : PK sur `id`, INDEX sur `started_at_utc`, INDEX composite sur `(mode, status)`.

#### 2.8.6 `progress_activity_zones` — Zones cardiaques/allure/puissance

Rôle : stocker le temps passé dans chaque zone (cardiaque, allure ou puissance) par activité.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | |
| `activity_id` | TEXT(36) | NOT NULL | Activité |
| `zone_type` | TEXT(32) | NOT NULL | Type de zone (`heart_rate`, `pace`, `power`) |
| `zone_name` | TEXT(16) | NOT NULL | Nom de la zone (`Z1`-`Z7`) |
| `range_low` | REAL | NULL | Borne inférieure de la zone |
| `range_high` | REAL | NULL | Borne supérieure de la zone |
| `time_s` | REAL | NOT NULL | Temps passé dans la zone en secondes |
| `time_pct` | REAL | NOT NULL | Pourcentage du temps total dans la zone |

**Index** : PK sur `id`, INDEX composite sur `(activity_id, zone_type)`.

**Utilisation** : alimente les graphiques de distribution par zone sur les pages de détail d'activité. Les zones sont calculées à partir des seuils utilisateur configurés dans `user_settings`.

#### 2.8.7 `progress_activity_splits` — Splits kilométriques

Rôle : stocker les splits kilométriques (ou par distance configurable) pour chaque activité.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | |
| `activity_id` | TEXT(36) | NOT NULL | Activité |
| `split_index` | INTEGER | NOT NULL | Numéro du split (0-based) |
| `distance_km` | REAL | NOT NULL | Distance cumulée au split en km |
| `time_s` | REAL | NOT NULL | Temps cumulé au split en secondes |
| `pace_s_per_km` | REAL | NULL | Allure du split en s/km |
| `elevation_gain_m` | REAL | NULL | Dénivelé positif du split en m |

**Index** : PK sur `id`, INDEX sur `activity_id`.

**Utilisation** : alimente le graphique de splits kilométriques sur la page de détail d'activité. Recalculé à chaque indexation lente si le Parquet a changé.

#### 2.8.8 `progress_activity_climbs` — Montées détectées

Rôle : stocker les segments de montée détectés automatiquement pour chaque activité.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | |
| `activity_id` | TEXT(36) | NOT NULL | Activité |
| `distance_km` | REAL | NOT NULL | Distance de la montée en km |
| `elevation_gain_m` | REAL | NOT NULL | Dénivelé positif de la montée en m |
| `avg_grade_percent` | REAL | NULL | Pente moyenne en % |
| `pace_s_per_km` | REAL | NULL | Allure sur la montée en s/km |
| `vam_m_h` | REAL | NULL | Vitesse ascensionnelle en m/h |
| `start_km` | REAL | NULL | Kilomètre de début de la montée |
| `end_km` | REAL | NULL | Kilomètre de fin de la montée |
| `duration_s` | REAL | NULL | Durée de la montée en secondes |

**Index** : PK sur `id`, INDEX sur `activity_id`.

**Utilisation** : alimente l'analyse des montées sur la page de détail d'activité et les comparaisons entre activités. Détection automatique basée sur la pente et le dénivelé cumulé.

#### 2.8.9 `progress_daily_aggregates` — Agrégats journaliers

Rôle : table indépendante contenant les agrégats quotidiens calculés à partir de `progress_activity_index`.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `date_utc` | TEXT(16) | PK | Date au format YYYY-MM-DD |
| `distance_m` | REAL | NULL | Distance totale en mètres |
| `moving_time_s` | REAL | NULL | Temps de mouvement total en secondes |
| `elapsed_time_s` | REAL | NULL | Temps total en secondes |
| `elevation_gain_m` | REAL | NULL | Dénivelé positif total en mètres |
| `trimp` | REAL | NULL | TRIMP total (somme des TRIMP par activité) |
| `activity_count` | INTEGER | NOT NULL, DEFAULT 0 | Nombre d'activités ce jour |
| `computed_at_utc` | TEXT | NOT NULL | Date de calcul de l'agrégat |

**Index** : PK sur `date_utc`.

**Cycle de vie** : recalculé à chaque indexation lente via agrégation `SUM`/`COUNT` sur `progress_activity_index` groupée par `local_date`. Les lignes sans `local_date` sont exclues.

---

## 3. Relations entre tables

```
activities (1) ────< activity_sources (N)
     │
     ├──< progress_activity_index (1)
     │        │
     │        ├──< progress_best_effort_points (N)
     │        ├──< progress_pace_hr_bins (N)
     │        ├─── progress_activity_tags (1)
     │        ├──< progress_activity_zones (N)
     │        ├──< progress_activity_splits (N)
     │        └──< progress_activity_climbs (N)
     │
     └─── (pas de FK explicite vers traces/goals)

progress_daily_aggregates (indépendant, agrégé depuis progress_activity_index)

sync_state (1) ──── (source = 'garmin')
sync_runs (N) ──── (source = 'garmin')

traces (1) ────< race_plans (N)
                    │
                    ├──< race_scenarios (N)
                    │      ├──< race_stops (N)
                    │      ├──< race_strategy_segments (N)
                    │      └──< race_nutrition_items (N)
                    ├──< race_equipment_items (N)
                    └──< race_course_points (N)
goals (indépendant)
user_settings (singleton, id=1)
```

**Remarques** :
- Il n'y a **pas de clé étrangère** entre `progress_activity_index.activity_id` et `activities.id`. La cohérence est maintenue par l'indexation fast (vérification FS ↔ DB).
- Les `activity_sources` ont une FK vers `activities`, avec `cascade='all, delete-orphan'` dans l'ORM (non traduit en contrainte SQLite).
- Les tables `progress_*` sont gérées comme un sous-système indépendant, sans FK vers `activities`.

---

## 4. Conventions de nommage

### 4.1 Noms de colonnes

| Règle | Exemple |
|---|---|
| Dates en UTC : suffixe `_utc` | `started_at_utc`, `created_at_utc` |
| Timestamps indexation : suffixe `_ts` | `start_ts_utc`, `indexed_at_ts` (⚠️ incohérence avec `_utc`) |
| Distances : suffixe `_m` ou `_km` | `distance_m`, `distance_km` |
| Allures : suffixe `_s_per_km` | `avg_pace_s_per_km` |
| FC : suffixe `_bpm` | `avg_hr_bpm` |
| Booléens : préfixe `has_` (INTEGER 0/1) | `has_hr`, `has_power` |
| Pourcentages : suffixe `_pct` | `decoupling_pct`, `stability_cv` (exception : CV sans `_pct`) |

> **Note** : La colonne `cardiac_drift_pct` a été supprimée de `progress_activity_index` (redondante avec `decoupling_pct`). Elle peut persister physiquement dans les bases créées avant SQLite 3.35.
| Dénivelé : suffixe `_m` | `elevation_gain_m` |

**Incohérence connue** : `start_ts_utc` (progress) vs `started_at_utc` (activities). Les deux désignent la même information. La forme `start_ts_utc` est utilisée dans les tables de progression, `started_at_utc` dans la table `activities`.

### 4.2 Types SQLite

SQLite ayant un typage dynamique, les types déclarés dans l'ORM sont indicatifs :

| Type ORM (SQLAlchemy) | Type stocké SQLite | Usage |
|---|---|---|
| `String(N)` / `Text` | TEXT | Identifiants, dates ISO, chemins |
| `Float` | REAL | Métriques numériques |
| `Integer` | INTEGER | Booléens (0/1), compteurs, durées |

### 4.3 Identifiants

- **UUID v4** (36 caractères) pour `activities.id`, `traces.id`, `goals.id`, `sync_runs.id` et les tables `race_*`.
- **INTEGER AUTOINCREMENT** pour les clés techniques (`activity_sources.id`, `progress_best_effort_points.id`, `progress_pace_hr_bins.id`).
- **VARCHAR source** comme PK pour `sync_state` (une ligne par source).

---

## 5. Accès aux données

### 5.1 Repositories

Chaque domaine métier a son repository dédié :

| Repository | Fichier | Tables gérées |
|---|---|---|
| `ActivityIndexRepository` | `backend/db/repository.py` | `activities`, `activity_sources`, `sync_state`, `sync_runs` |
| `ProgressRepository` | `backend/db/progress_repository.py` | `progress_activity_index`, `progress_best_effort_points`, `progress_pace_hr_bins`, `progress_activity_tags` |
| `TraceRepository` | `backend/db/trace_repository.py` | `traces` |
| `RacePlanRepository` | `backend/db/race_plan_repository.py` | `race_plans`, `race_scenarios`, `race_stops`, `race_strategy_segments`, `race_nutrition_items`, `race_equipment_items`, `race_course_points` |
| `GoalsRepository` | `backend/db/goals_repository.py` | `goals` |
| `SettingsRepository` | `backend/db/settings_repository.py` | `user_settings` |

### 5.2 Pattern d'utilisation

Tous les repositories suivent le même pattern :

```python
# Obtention d'une session
session = db_session_factory()

try:
    repo = ProgressRepository()
    rows = repo.list_activity_rows(session, from_ts_utc=..., to_ts_utc=...)
    # travail avec rows...
    session.commit()
finally:
    session.close()
```

La session factory est injectée dans `app.state.db_session_factory` au démarrage et récupérée par les routes via `getattr(request.app.state, "db_session_factory", None)`.

### 5.3 Transactions

- `autoflush=False` : les modifications ne sont pas automatiquement flushées.
- `autocommit=False` : chaque modification nécessite un `session.commit()` explicite.
- Les repositories lèvent des exceptions en cas d'erreur ; les routes appellent `session.rollback()` dans le `except`.

---

## 6. Migrations

Les migrations historiques restent gérées dans `backend/db/session.py`. La préparation de course ajoute un runner idempotent versionné dans `backend/db/migrations/`.

1. `Base.metadata.create_all()` crée les tables absentes.
2. `backend/db/migrations/20260714_race_planning.py` crée les tables `race_*` et ajoute les quatre colonnes Parquet de `traces`.
3. La migration inscrit `20260714_race_planning` dans `schema_migrations`.
4. `init_db()` applique automatiquement la migration ; elle peut aussi être lancée manuellement.

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m db.migrations.run
Pop-Location
```

**Colonnes ajoutées par migration** (ordre chronologique) :

| Table | Colonne | Date approximative |
|---|---|---|
| `activities` | `progress_indexed_at_utc` | ~2026-02 |
| `activities` | `progress_rollup_path` | ~2026-02 |
| `goals` | `location_city` | ~2026-02 |
| `goals` | `location_country` | ~2026-02 |
| `goals` | `location_country_code` | ~2026-02 |
| `goals` | `location_lat` | ~2026-02 |
| `goals` | `location_lon` | ~2026-02 |
| `user_settings` | `vo2max_lastest` | ~2026-02 |
| `progress_activity_index` | `vo2max` | ~2026-03 |
| `progress_activity_index` | `fast_indexation_date` | ~2026-03 |
| `progress_activity_index` | `slow_indexation_date` | ~2026-03 |
| `progress_activity_index` | `elevation_loss_m`, `pace_first_half_s_per_km`, `pace_second_half_s_per_km`, `power_normalized_w`, `power_intensity_factor`, `power_tss`, `cadence_mean_spm`, `cadence_max_spm` | 2026-06 |
| `progress_activity_index` | (suppression) `cardiac_drift_pct` | 2026-06 |
| `traces` | `parquet_path`, `parquet_source_hash_sha256`, `dataframe_schema_version`, `parquet_generated_at_utc` | 2026-07 |

> **Nouvelles tables de préparation** : `race_plans`, `race_scenarios`, `race_stops`, `race_strategy_segments`, `race_nutrition_items`, `race_equipment_items`, `race_course_points` et `schema_migrations`.

**Limites** : la migration de préparation est montante uniquement et ne fournit pas de rollback automatique. Elle prend en charge SQLite et PostgreSQL pour les ajouts concernés.

---

## 7. Commandes de diagnostic

### Vérifier le schéma

```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/coursescope.sqlite')
for row in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\"):
    print(row[0])
conn.close()
"
```

### Compter les lignes par table

```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/coursescope.sqlite')
tables = [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")]
for t in tables:
    cnt = conn.execute(f'SELECT COUNT(*) FROM \"{t}\"').fetchone()[0]
    print(f'{t}: {cnt}')
conn.close()
"
```

### Voir le détail d'une table

```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/coursescope.sqlite')
for row in conn.execute('PRAGMA table_info(\"progress_activity_index\")'):
    print(row)
conn.close()
"
```

### Vérifier la cohérence FS ↔ DB

```bash
curl -X POST http://localhost:8000/progress/verify
curl http://localhost:8000/progress/verify-status
```

---

## 8. Références croisées

| Document | Lien |
|---|---|
| Préparation de course et contrats des traces | `docs/race-planning.md` |
| Architecture d'indexation | `docs/indexation.md` |
| Page progression (dashboard) | `docs/progression.md` |
| Catalogue des endpoints API | `docs/metrics_catalog.md` |
| Procédure d'indexation opérationnelle | `docs/indexation_operational_runbook.md` |
| Modèles ORM | `backend/db/models.py` |
| Session et migrations | `backend/db/session.py` |
| Repositories | `backend/db/repository.py`, `progress_repository.py`, `trace_repository.py`, `goals_repository.py`, `settings_repository.py` |
