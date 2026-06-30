# Modifications à implémenter — CourseScope

Date : 2026-06-30 16:30
Source : agents/modifications.txt
Produit par : agents/agent-brainstorm.md
Statut : prêt pour agent-dev

## 1. Résumé exécutif

L'utilisateur demande l'élimination de la redondance backend identifiée dans `docs/audit_application.md` (Section 4, Tableau « Backend — 16 fonctions dupliquées ») et la gestion des 6 endpoints non utilisés (Section 8).

**Périmètre retenu** : extraction des fonctions dupliquées dans des modules partagés + suppression du code mort + unification des helpers de route dupliqués (pattern `temp_storage` fallback, erreur handling).

**Périmètre exclu** (intentionnellement) : découpage des monolithes (>500 lignes), migration FastAPI DI, suppression des vues legacy — ces chantiers sont volontairement différés par l'audit (Section 12) pour cause de risque de régression élevé.

**Priorisation** :
- **P0** : Extraction des fonctions dupliquées + suppression du code mort (faible risque, fort impact)
- **P1** : Unification des helpers de route dupliqués (10+ répétitions, fort impact maintenabilité)
- **P2** : Gestion des endpoints non utilisés (suppression)

Au total : **14 actions** (8 P0, 3 P1, 3 P2). 3 nouveaux fichiers créés. Aucune modification de comportement utilisateur.

## 2. Demandes utilisateur extraites

### Demande 1 — Élimination de la redondance backend

- **Texte source** : « modification de la redondance backend, comme décrit dans docs\audit_application.md »
- **Interprétation** : L'utilisateur veut appliquer les recommandations « court terme » de l'audit concernant spécifiquement le backend, à savoir l'extraction des fonctions dupliquées et la gestion des endpoints non utilisés.
- **Statut** : retenue
- **Justification** : La demande est explicite et s'appuie sur un audit existant. Changements à faible risque, amélioration directe de la maintenabilité.

## 3. Diagnostic de l'existant

### 3.1 Fichiers et zones lus

- `docs/audit_application.md` — Sections 4, 8, 10, 12
- `agents/AGENTS.md` — Règles globales
- `agents/agent-dev.md` — Contraintes d'implémentation
- `backend/api/main.py` — Route registration dual-path, get_activity_storage, get_series_registry
- `backend/api/routes/activities.py` — _model_to_dict (l.30), get_activity_storage (l.26)
- `backend/api/routes/series.py` — _model_to_dict (l.11), get_series_registry (l.17)
- `backend/api/routes/analysis.py` — get_series_registry (l.125), pattern temp_storage (×4), _started_at_utc_from_df
- `backend/api/routes/progress.py` — _parse_csv_floats, _parse_ts_utc
- `backend/api/routes/maps.py` — pattern temp_storage (×1)
- `backend/api/routes/traces.py` — pattern temp_storage (×3)
- `backend/storage/activity_store.py` — _model_to_dict (l.22), _parse_iso_datetime (l.32), _to_utc (l.45), _infer_started_at_utc (l.138), _compute_sidebar_stats (l.164)
- `backend/progress/indexer.py` — _parse_iso_datetime (l.34), _to_utc (l.43), _infer_started_at_utc_from_df (l.54), _format_ts_utc (l.49)
- `backend/progress/indexation_runner.py` — _now_utc_iso, _read_json, _parse_iso, _find_original_path
- `backend/progress/verify_index.py` — _read_json (l.40), _parse_iso (l.44), _find_original_path (l.60)
- `backend/progress/verify_runner.py` — _now_utc_iso (l.41), _snapshot_state_unlocked (l.26)
- `backend/core/metrics.py` — _weighted_mean (l.72), _compute_grade_percent_from_elevation (l.192)
- `backend/core/real_run_analysis.py` — _weighted_mean (l.64), _unique_xy (l.317 et l.1237), _compute_grade_percent (l.930)
- `backend/core/utils.py` — seconds_to_mmss
- `backend/core/grade_table.py` — pace_to_mmss (l.80, doublon mort)
- `backend/core/parsing.py` — parse_km_list (non utilisé en production)
- `backend/core/theoretical_model.py` — elevation gain calc dupliquée
- `backend/core/stats/basic_stats.py` — elevation gain calc dupliquée
- `backend/api/compat.py` — LoadedActivity adapter (42 lignes, code mort)
- `backend/services/history_service.py` — upsert_history (19 lignes, code mort)
- `backend/services/cache.py` — MemoryCache (l.47), DiskCache (l.88), sha256_bytes (l.27)
- `backend/integrations/garmin/sync_service.py` — _sha256_bytes (l.29)
- `backend/api/schemas.py` — SidebarStats (Pydantic)

### 3.2 Constats établis

1. **`_model_to_dict`** défini 3 fois : activities.py:30, series.py:11, activity_store.py:22. Identique.
2. **`get_activity_storage`** défini 2 fois : main.py:187 (inutilisé), activities.py:26 (utilisé par les routes).
3. **`get_series_registry`** défini 3 fois : main.py:191, analysis.py:125, series.py:17. Identiques.
4. **`_weighted_mean`** défini 2 fois : metrics.py:72, real_run_analysis.py:64. Identique.
5. **`_parse_iso_datetime` + `_to_utc`** dupliqués entre activity_store.py et indexer.py.
6. **`_infer_started_at_utc`** dupliqué entre activity_store.py:138 et indexer.py:54 (nom différent).
7. **`_sha256_bytes`** dupliqué entre sync_service.py:29 et cache.py:27 (`sha256_bytes` public).
8. **`_unique_xy`** défini 2 fois dans real_run_analysis.py (l.317 et l.1237).
9. **`_read_json`, `_parse_iso`, `_find_original_path`** dupliqués entre indexation_runner.py et verify_index.py.
10. **`_now_utc_iso`** dans indexation_runner.py et verify_runner.py — `db/models.py:utc_now_iso()` existe déjà.
11. **`_snapshot_state_unlocked`** pattern commun entre indexation_runner.py et verify_runner.py.
12. **Calcul d'elevation gain** (`np.clip(np.diff(elevation), 0, None).sum()`) 7+ occurrences.
13. **Pattern `temp_storage` fallback** répété 10 fois dans analysis.py (×4), series.py (×2), maps.py (×1), traces.py (×3).
14. **Code mort** : `api/compat.py` (42 lignes), `history_service.py` (19 lignes), `MemoryCache` + `DiskCache` dans cache.py (66 lignes), `pace_to_mmss` dans grade_table.py (6 lignes), `parse_km_list` dans parsing.py.
15. **Endpoints non utilisés** : `/health`, `/progress/verify`, `/progress/verify-status`.
16. **Dual-path registration** (main.py:163-184) est intentionnel → préservé (AGENTS.md §5.3).

### 3.3 Hypothèses

- La suppression des fonctions dupliquées ne cassera pas les imports existants si les nouveaux modules sont correctement ajoutés au PYTHONPATH.
- Les endpoints `/progress/verify` et `/progress/verify-status` sont remplacés par fast/slow — suppression sans danger.
- `backend/core/utils.py` est l'emplacement naturel pour les utilitaires mathématiques partagés.
- `backend/progress/_utils.py` (à créer) pour les utilitaires d'indexation.
- `backend/api/_helpers.py` (à créer) pour les helpers de route.

### 3.4 Incertitudes

- Impact exact sur les tests unitaires — nécessite lancement complet après chaque étape.
- `/health` pourrait être consommé par Docker — vérifier Dockerfile avant suppression.
- `verify_index.py` partiellement importé par `indexation_runner.py` (deux fonctions) → ne pas supprimer entièrement.

## 4. Spécification fonctionnelle cible

Aucun changement fonctionnel. L'objectif est purement structurel : éliminer la duplication sans modifier le comportement observable.

**Contrat de non-régression** :
- Tous les endpoints conservent signatures et réponses.
- Compatibilité `/xxx` et `/api/xxx` préservée.
- Données stockées inchangées.
- Tests existants continuent de passer.

## 5. Spécification technique proposée

### 5.1 Création de `backend/core/_shared.py` — Utilitaires mathématiques

Contenu :
- `_weighted_mean(values, weights)` — extrait de metrics.py:72
- `_unique_xy(x, y)` — extrait de real_run_analysis.py:317
- `compute_elevation_gain(elevation_array)` — `np.clip(np.diff(elevation), 0, None).sum()`
- `compute_elevation_loss(elevation_array)` — `np.clip(np.diff(elevation), None, 0).sum()`

Fichiers impactés (6) : metrics.py (supprimer _weighted_mean), real_run_analysis.py (supprimer _weighted_mean + 2× _unique_xy + remplacer calculs elevation), theoretical_model.py (remplacer calcul inline), basic_stats.py (remplacer _elevation_gain_loss), trace_store.py (remplacer calcul), analysis.py (remplacer calcul l.718).

### 5.2 Création de `backend/progress/_utils.py` — Utilitaires d'indexation

Contenu :
- `_read_json(path)` — extrait de verify_index.py:40
- `_parse_iso(value)` → `str | None` — extrait de verify_index.py:44
- `_parse_iso_datetime(value)` → `datetime | None` — extrait de indexer.py:34
- `_to_utc(dt)` → `datetime` — extrait de indexer.py:43
- `_format_ts_utc(dt)` → `str` — extrait de indexer.py:49
- `_infer_started_at_utc_from_df(df)` → `str | None` — extrait de indexer.py:54
- `_find_original_path(activity_dir)` → `str | None` — extrait de verify_index.py:60
- `_find_original_fit_path(activity_dir)` → `str | None` — extrait des fichiers concernés

Fichiers impactés (5) : indexation_runner.py (remplacer _read_json, _parse_iso, _find_original_path, _now_utc_iso), verify_index.py (remplacer _read_json, _parse_iso, _find_original_path), indexer.py (remplacer _parse_iso_datetime, _to_utc, _format_ts_utc, _infer_started_at_utc_from_df), activity_store.py (remplacer _parse_iso_datetime, _to_utc, _infer_started_at_utc), verify_runner.py (si conservé : remplacer _now_utc_iso → utc_now_iso()).

### 5.3 Création de `backend/api/_helpers.py` — Helpers de route

Contenu :
- `_model_to_dict(model)` — version Pydantic v1+v2 (de activity_store.py)
- `resolve_activity_df(request, activity_id)` — pattern temp_storage fallback
- `get_series_registry(request)` — unifié
- `get_activity_storage(request)` — unifié

Fichiers impactés (7) : analysis.py (×4 pattern + get_series_registry), series.py (×2 pattern + get_series_registry + _model_to_dict), maps.py (×1 pattern), traces.py (×3 pattern), activities.py (get_activity_storage + _model_to_dict), main.py (supprimer get_activity_storage l.187, get_series_registry l.191), activity_store.py (_model_to_dict).

### 5.4 Suppression du code mort

| Fichier | Action |
|---|---|
| `backend/api/compat.py` | Supprimer le fichier (42 lignes) |
| `backend/services/history_service.py` | Supprimer le fichier (19 lignes) |
| `backend/services/cache.py` | Supprimer `MemoryCache` (l.47-86) et `DiskCache` (l.88-113) |
| `backend/core/grade_table.py` | Supprimer `pace_to_mmss` (l.80-86) |
| `backend/core/parsing.py` | Supprimer le fichier (23 lignes), sauf si utilisé par des tests |

### 5.5 Unification des doublons restants

- **`_sha256_bytes`** dans sync_service.py → importer `sha256_bytes` depuis `services.cache`
- **`_now_utc_iso`** dans indexation_runner.py et verify_runner.py → importer `utc_now_iso()` depuis `db.models`

### 5.6 Gestion des endpoints non utilisés

| Endpoint | Action | Justification |
|---|---|---|
| `GET /health` | Supprimer (main.py:205-224) | Non consommé, sauf si Docker HEALTHCHECK |
| `POST /progress/verify` | Supprimer | Remplacé par fast/slow |
| `GET /progress/verify-status` | Supprimer | Remplacé par index/status |
| `GET /activity/{id}/series` | Conserver | Utile debug |
| `GET /progress/session-taxonomy` | Conserver | Future UI (P2 séparé) |
| `POST /progress/tags` | Conserver | Future UI (P2 séparé) |

**⚠️ Vérification préalable** : `grep -r "verify_index" backend/progress/indexation_runner.py` → les fonctions `_maybe_backfill_vo2max_from_fit` et `_sync_vo2max_latest_from_index` sont importées. Les déplacer dans `progress/_utils.py` avant toute suppression de verify_index.py.

### 5.7 Documentation

- Mettre à jour `CHANGELOG.md` avec entrée « Refactor: extraction des fonctions dupliquées backend »
- Mettre à jour `docs/audit_application.md` §12 : marquer « Extraction des fonctions dupliquées backend » ✅

## 6. Plan d'implémentation pour agent-dev

### Étape 1 — P0 : Créer `backend/core/_shared.py`

- **Objectif** : Centraliser _weighted_mean, _unique_xy, compute_elevation_gain, compute_elevation_loss
- **Fichiers** :
  - `backend/core/_shared.py` (création)
  - `backend/core/metrics.py` (supprimer _weighted_mean l.72-77, importer depuis _shared)
  - `backend/core/real_run_analysis.py` (supprimer _weighted_mean l.64-76, supprimer les 2 _unique_xy internes l.317 + l.1237, importer depuis _shared)
  - `backend/core/theoretical_model.py` (remplacer calcul elevation inline l.180 par compute_elevation_gain)
  - `backend/core/stats/basic_stats.py` (remplacer _elevation_gain_loss l.58-67 par compute_elevation_gain/loss)
  - `backend/storage/trace_store.py` (remplacer calcul l.59)
  - `backend/api/routes/analysis.py` (remplacer calcul l.718)
- **Tests** : `python -m pytest tests/unit/ -k "metrics or real_run" -q`
- **Risques** : _unique_xy utilise des closures → après extraction, signature = (x, y). Vérifier les appels dans compute_splits et compute_climbs.

### Étape 2 — P0 : Créer `backend/progress/_utils.py`

- **Objectif** : Centraliser _read_json, _parse_iso, _parse_iso_datetime, _to_utc, _format_ts_utc, _infer_started_at_utc_from_df, _find_original_path, _find_original_fit_path
- **Fichiers** :
  - `backend/progress/_utils.py` (création)
  - `backend/progress/indexation_runner.py` (remplacer définitions par imports)
  - `backend/progress/verify_index.py` (remplacer définitions par imports)
  - `backend/progress/indexer.py` (remplacer définitions par imports)
  - `backend/storage/activity_store.py` (remplacer _parse_iso_datetime, _to_utc, _infer_started_at_utc par imports)
- **Tests** : `python -m pytest tests/unit/ -q`
- **Risques** : Import circulaire → _utils.py ne doit rien importer de progress/. Vérifier.

### Étape 3 — P0 : Créer `backend/api/_helpers.py`

- **Objectif** : Centraliser _model_to_dict, resolve_activity_df, get_series_registry, get_activity_storage
- **Fichiers** :
  - `backend/api/_helpers.py` (création)
  - `backend/api/routes/analysis.py` (remplacer ×4 pattern + get_series_registry)
  - `backend/api/routes/series.py` (remplacer ×2 pattern + get_series_registry + _model_to_dict)
  - `backend/api/routes/maps.py` (remplacer ×1 pattern)
  - `backend/api/routes/traces.py` (remplacer ×3 pattern)
  - `backend/api/routes/activities.py` (remplacer get_activity_storage + _model_to_dict)
  - `backend/api/main.py` (supprimer get_activity_storage l.187-188, get_series_registry l.191-192)
  - `backend/storage/activity_store.py` (supprimer _model_to_dict l.22-24)
- **Tests** : `python -m pytest tests/pytest/ -q`
- **Risques** : resolve_activity_df doit gérer le fallback temp_storage et lever FileNotFoundError si aucune source.

### Étape 4 — P0 : Supprimer le code mort

- **Objectif** : Éliminer fichiers et fonctions jamais utilisés
- **Fichiers** : `api/compat.py` (suppr.), `services/history_service.py` (suppr.), `services/cache.py` (suppr. MemoryCache + DiskCache), `core/grade_table.py` (suppr. pace_to_mmss), `core/parsing.py` (suppr. si non utilisé en tests)
- **Vérifications préalables** :
  - `grep -r "from api.compat\|import.*compat" backend/ tests/ scripts/`
  - `grep -r "history_service\|upsert_history" backend/` (hors tests)
  - `grep -r "MemoryCache\|DiskCache" backend/ tests/ scripts/`
  - `grep -r "parse_km_list\|from core.parsing" .`
- **Tests** : `python -m compileall backend`
- **Risques** : Si un script externe importe ces modules, la suppression cassera. Vérifier `scripts/`.

### Étape 5 — P0 : Unifier `_sha256_bytes`

- **Objectif** : sync_service.py utilise sha256_bytes de cache.py
- **Fichier** : `backend/integrations/garmin/sync_service.py` → supprimer _sha256_bytes l.29-30, importer sha256_bytes
- **Tests** : `python -m pytest tests/ -k "garmin" -q`

### Étape 6 — P0 : Remplacer `_now_utc_iso` par `utc_now_iso()`

- **Objectif** : Utiliser la fonction existante de db/models.py
- **Fichiers** : `indexation_runner.py`, `verify_runner.py` → remplacer _now_utc_iso() par utc_now_iso() (déjà importé)
- **Tests** : `python -m pytest tests/ -k "progress" -q`

### Étape 7 — P2 : Supprimer `/health`

- **Objectif** : Supprimer le handler non utilisé
- **Fichiers** : `backend/api/main.py` (suppr. l.205-224), `frontend/src/lib/api.ts` (suppr. healthCheck si présent)
- **Vérification** : `grep "HEALTHCHECK\|/health" Dockerfile docker-compose.yml 2>$null`
- **Tests** : `python -m pytest tests/pytest/ -q`

### Étape 8 — P2 : Déplacer les fonctions encore utilisées de `verify_index.py`

- **Objectif** : Avant de supprimer verify_index.py, déplacer _maybe_backfill_vo2max_from_fit et _sync_vo2max_latest_from_index dans progress/_utils.py
- **Fichier** : `backend/progress/_utils.py` (ajout), `backend/progress/indexation_runner.py` (mise à jour import l.29)
- **Tests** : `python -m pytest tests/unit/ -q`

### Étape 9 — P2 : Supprimer `/progress/verify` et `/progress/verify-status`

- **Objectif** : Supprimer les endpoints et le code associé
- **Fichiers** :
  - `backend/api/routes/progress.py` (suppr. handlers verify et verify-status)
  - `backend/progress/verify_runner.py` (suppr. fichier entier 84 lignes)
  - `backend/progress/verify_index.py` (suppr. fichier entier après déplacement des fonctions → étape 8)
  - `frontend/src/lib/api.ts` (suppr. verify, verifyStatus si présents)
- **Tests** : `python -m pytest tests/ -q -k "not verify"`

### Étape 10 — Vérification globale

- **Commandes** :
  ```bash
  python -m compileall backend
  python -m pytest tests/unit/ -q
  python -m pytest tests/pytest/ -q
  cd frontend && npm test && npm run build
  ```

### Étape 11 — Documentation

- **Fichiers** : `CHANGELOG.md`, `docs/audit_application.md` §12
- **Action** : Ajouter entrée refactor, marquer ✅

## 7. Tests et vérifications attendus

Backend :
```bash
python -m compileall backend
python -m pytest tests/unit/ -q
python -m pytest tests/pytest/ -q
```

Frontend :
```bash
cd frontend
npm test
npm run build
```

## 8. Critères d'acceptation

- [ ] `backend/core/_shared.py` existe avec _weighted_mean, _unique_xy, compute_elevation_gain, compute_elevation_loss
- [ ] `backend/progress/_utils.py` existe avec tous les utilitaires d'indexation
- [ ] `backend/api/_helpers.py` existe avec _model_to_dict, resolve_activity_df, get_series_registry, get_activity_storage
- [ ] Les 3 copies de _model_to_dict sont supprimées, un seul import
- [ ] Les 2 copies de _weighted_mean sont supprimées, un seul import
- [ ] Les 10 occurrences du pattern temp_storage sont remplacées par resolve_activity_df()
- [ ] `backend/api/compat.py` supprimé
- [ ] `backend/services/history_service.py` supprimé
- [ ] MemoryCache et DiskCache supprimés de cache.py
- [ ] pace_to_mmss supprimé de grade_table.py
- [ ] _sha256_bytes dans sync_service.py → import sha256_bytes
- [ ] _now_utc_iso() → utc_now_iso() dans indexation_runner.py et verify_runner.py
- [ ] /health, /progress/verify, /progress/verify-status supprimés
- [ ] `python -m compileall backend` 0 erreur
- [ ] `python -m pytest tests/unit/ -q` tous les tests passent
- [ ] `python -m pytest tests/pytest/ -q` tous les tests passent
- [ ] `cd frontend && npm test` passe
- [ ] `cd frontend && npm run build` passe

## 9. Risques et garde-fous

1. **Import circulaire progress/_utils.py** → _utils.py ne doit rien importer de progress/.
2. **verify_index.py partiellement importé** → déplacer _maybe_backfill_vo2max_from_fit et _sync_vo2max_latest_from_index avant suppression (étape 8).
3. **parse_km_list utilisé hors backend/** → grep global avant suppression.
4. **_unique_xy change de signature** (closure → paramètres) → vérifier compute_splits et compute_climbs.
5. **Docker HEALTHCHECK** → vérifier Dockerfile avant suppression /health.
6. **Fonctions main.py supprimées** → grep `main.get_activity_storage\|main.get_series_registry` avant suppression.

## 10. Décisions prises par agent-brainstorm

1. **Périmètre backend uniquement** — les redondances frontend (dateUtils, chartUtils, paceUtils) sont hors scope.
2. **Exclusion du découpage des monolithes** — différé par l'audit §12.
3. **3 nouveaux modules** — core/_shared.py, progress/_utils.py, api/_helpers.py — un par couche.
4. **Conservation session-taxonomy et tags** — valeur métier, UI future.
5. **Suppression /health** — non consommé (vérifier Docker).
6. **Préservation dual-path `/xxx` et `/api/xxx`** — AGENTS.md §5.3.
7. **Non-inclusion SidebarStats/compute_sidebar_stats** — problème architectural plus large (frontière API↔Services), hors scope.

## 11. Points à ne pas faire

- ❌ Ne pas découper real_run_analysis.py, progress.py, analysis.py, metrics.py (monolithes)
- ❌ Ne pas modifier les schémas Pydantic ni les contrats API
- ❌ Ne pas supprimer verify_index.py sans avoir déplacé les fonctions encore utilisées
- ❌ Ne pas modifier la registration dual-path dans main.py:163-184
- ❌ Ne pas ajouter de nouvelle dépendance Python
- ❌ Ne pas modifier les données stockées
- ❌ Ne pas committer ni pousser
