# Indexation — Architecture

> **Type** : Spécification · **Statut** : ✅ Implémentée
> **Dernière mise à jour** : 2026-02-23

Ce document est la référence de l'indexation CourseScope.

**Périmètre** : architecture fast/slow, contrats de données, API, invariants de stabilité et performance.

## 1) Vue d ensemble

Le systeme d indexation est compose de 2 modes complementaires:

1. `Indexation rapide (fast)`
- Role: synchroniser l inventaire des activites entre filesystem et table `activities`
- Nature: controle structurel, sans recalcul metrique lourd
- Declenchement: evenementiel (sync, page `/progress`, action manuelle)

2. `Indexation complete (slow)`
- Role: recalculer et verifier les metriques analytiques
- Nature: controle analytique complet, potentiellement couteux
- Declenchement: conditionnel (delta fast) ou explicite utilisateur

Objectif global:
- Minimiser les recalculs
- Preserver la reactivite UI
- Garantir la coherence des donnees

## 2) Source de verite et responsabilites

### 2.1 Sources de verite

- Activites de reference: table `activities`
- Donnees brutes: `data/activities/<activity_id>/meta.json` et `data/activities/<activity_id>/df.parquet`
- Index analytique: `progress_activity_index` et tables derivees

### 2.2 Separation stricte des roles

- Fast:
  - Detecte ajouts/suppressions
  - Repare les ecarts FS <-> DB
  - Ne calcule pas de metriques derivees lourdes

- Slow:
  - Reindexe les activites necessaires
  - Met a jour index principal et tables derivees
  - Met a jour les artefacts de trace analytique

## 3) Contrat de l indexation rapide

### 3.1 Entrees

- Dossiers activites valides sur disque
- IDs existants en base (`activities.id`)

### 3.2 Algorithme

1) Construire `fs_ids`
2) Construire `db_ids`
3) Calculer:
- `missing_on_disk = db_ids - fs_ids`
- `missing_in_db = fs_ids - db_ids`
4) Appliquer:
- Suppression en base pour `missing_on_disk` (avec nettoyage des tables liees)
- Creation en base pour `missing_in_db` (a partir de `meta.json` + paths)
5) Retourner un resultat de run

### 3.3 Sorties

- `scanned`: nombre de dossiers valides analyses
- `added`: nombre d activites ajoutees en DB
- `deleted`: nombre d activites supprimees de la DB
- `errors`: nombre d erreurs

### 3.4 Post-condition

Si `added + deleted > 0`, une slow incremental est lancee automatiquement.

## 4) Contrat de l indexation complete

### 4.1 Entrees

- Ensemble des activites de la table `activities`
- Donnees brutes associees (`meta.json`, `df.parquet`)
- Etat analytique courant (`progress_activity_index`)

### 4.2 Criteres de reindexation

Une activite est reindexee si au moins un critere est vrai:
- Ligne absente dans `progress_activity_index`
- Fingerprint modifie
- `metrics_version` obsolete
- Champ critique manquant
- Mode force (`backfill_full`)

### 4.3 Sorties

- Index analytique a jour par activite
- Tables derivees synchronisees
- Horodatages d indexation renseignes
- Artefact analytique par activite regenere

### 4.4 Strategies supportees

- `incremental`: traite uniquement les activites stale
- `backfill_missing`: traite les activites non indexees
- `backfill_full`: recalcule tout

## 5) Etat d execution et observabilite

### 5.1 Etat runtime unifie

- `running: bool`
- `mode: "fast" | "slow" | null`
- `phase: "prepare" | "scan_fs" | "sync_db" | "recompute" | "finalize" | null`
- `started_at_utc: string | null`
- `finished_at_utc: string | null`
- `progress_current: int`
- `progress_total: int`
- `last_error: string | null`
- `last_result: { scanned, added, deleted, indexed, up_to_date, errors, skipped }`

### 5.2 Concurrence

- Un seul run actif a la fois
- Un nouveau trigger pendant un run renvoie l etat en cours

### 5.3 Historique persistant (recommande)

Table `progress_indexation_runs`:
- `id`, `mode`, `strategy`, `reason`, `status`
- `started_at_utc`, `finished_at_utc`
- `duration_ms` (obligatoire, calcule pour chaque run fast ou slow)
- `progress_total`, `progress_done`
- `result_json`, `error`

## 6) Modele de donnees indexation

### 6.1 Tracabilite par activite

Dans `progress_activity_index`, deux colonnes de suivi:
- `fast_indexation_date`
- `slow_indexation_date`

Ces champs representent la derniere execution connue par activite.

### 6.2 Invariants de coherence

- `progress_activity_index.activity_id` correspond a un `activities.id` valide
- Les suppressions d activites nettoient les tables derivees associees
- Les tables derivees restent sans doublon
- `metrics_version` pilote les reindexations fonctionnelles

## 7) API indexation

### 7.1 Endpoints

- `POST /progress/index/fast`
- `POST /progress/index/slow`
- `GET /progress/index/status`

### 7.2 Contrat status

Reponse type:
- `running`
- `mode`
- `phase`
- `current_run_duration_ms` (si run actif)
- `progress_current`
- `progress_total`
- `percent`
- `last_result`
- `last_error`
- `last_started_at_utc`
- `last_finished_at_utc`
- `last_duration_ms`

### 7.3 Contrat trigger slow

Payload attendu:
- `strategy: incremental | backfill_missing | backfill_full`
- `reason: string`
- `force: boolean`

## 8) Triggers metier

### 8.1 Fast auto

La fast peut etre declenchee automatiquement:
- Apres synchronisation activites
- A l ouverture de `/progress`
- Via bouton manuel

### 8.2 Slow conditionnelle

La slow est declenchee:
- Apres delta fast
- Par action utilisateur explicite

### 8.3 Boutons maintenance

- `Indexation rapide`: lance uniquement fast
- `Indexation complete`: lance fast puis slow forcee

## 9) UI/UX de suivi

### 9.1 Parametres > Maintenance

- Deux boutons d action (`rapide`, `complete`)
- Etat textualise par mode (fast/slow)
- Barre de progression bleue pendant run
- Resume chiffre du dernier run

### 9.2 Page `/progress`

- Trigger fast au mount
- Polling status tant que run actif
- Rendu des graphes non bloquant

## 10) Performance et fiabilite

### 10.1 Cibles

- Fast en cout lineaire sur volume activites, sans parse massif des parquets
- Slow incremental prioritaire pour limiter le volume de recalcul
- Etat API de status rapidement disponible

### 10.2 SQLite

- WAL active
- Busy timeout configure
- Commits batches
- Contention geree (retry/backoff)

### 10.3 Reprise

- Checkpoints regulierement persistes
- Run rejouable sans corruption ni duplication

## 11) Tests obligatoires

Backend:
- Fast add/remove
- Slow stale detection (fingerprint/version/champs critiques)
- Idempotence des relances
- Concurrence: un seul run actif

API:
- Demarrage fast/slow
- Format status stable
- Gestion run deja en cours

Frontend:
- Affichage boutons et etat
- Polling et progression
- Flux `/progress` non bloquant

## 12) Definition of done

La nouvelle architecture est consideree complete quand:
- Les 3 endpoints indexation sont en place
- Le mode fast/slow est operationnel et observable
- Les invariants de coherence sont verifies
- L UI expose un suivi clair des executions
- Les tests critiques passent sans regression

## 13) Runbook operationnel

Procedure de deploiement/migration et rollback:

- `docs/indexation_operational_runbook.md`
