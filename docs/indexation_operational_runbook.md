# Runbook operationnel - Indexation

Ce runbook decrit la procedure de deploiement et de verification pour la migration indexation fast/slow.

## 1. Pre-requis

- Branche a deployer: `main`
- Base SQLite accessible en lecture/ecriture
- Variable `COURSESCOPE_DATA_DIR` correctement configuree
- Sauvegarde du dossier `data/` effectuee

## 2. Checklist pre-deploiement

1. Verifier que les endpoints existent:
   - `POST /progress/index/fast`
   - `POST /progress/index/slow`
   - `GET /progress/index/status`
2. Verifier les colonnes DB:
   - `progress_activity_index.fast_indexation_date`
   - `progress_activity_index.slow_indexation_date`
   - `activities.progress_indexed_at_utc`
   - `activities.progress_rollup_path`
3. Verifier que les tests critiques passent:
   - `tests/pytest/test_progress_indexation_runner.py`
   - `tests/pytest/test_progress_endpoints.py`

## 3. Procedure de migration

1. Deployer l'application (backend + frontend) sur `main`.
2. Lancer une indexation rapide:
   - `POST /progress/index/fast`
3. Attendre `running=false` sur `GET /progress/index/status`.
4. Lancer une indexation complete forcee:
   - `POST /progress/index/slow` avec payload:
     ```json
     {"strategy":"backfill_full","reason":"runbook_migration","force":true}
     ```
5. Verifier la fin du run et l'absence d'erreur (`last_error=null`).

## 4. Verification post-deploiement

1. Ouvrir `/settings`:
   - Boutons `Indexation rapide` et `Indexation complete` visibles
   - Barre de progression visible pendant run
2. Ouvrir `/progress`:
   - Trigger fast auto au mount
   - UI non bloquante pendant l'indexation
3. Verifier l'historique runs (`progress_indexation_runs`):
   - `mode`, `strategy`, `reason`, `status`, `duration_ms`, `result_json`

## 5. Rollback

En cas d'incident:

1. Stopper le trafic applicatif.
2. Restaurer la sauvegarde `data/` et la base SQLite.
3. Redeployer la version precedente.
4. Executer un `POST /progress/index/fast` pour re-synchroniser FS/DB.

## 6. Observabilite minimale

- Surveiller `last_error` via `GET /progress/index/status`
- Surveiller les statuts `failed` dans `progress_indexation_runs`
- Surveiller les logs backend autour de:
  - `fast_indexation_add_failed`
  - `slow_indexation_failed`
  - `garmin_sync_fast_indexation_trigger_failed`
