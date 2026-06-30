# Modifications à implémenter — CourseScope

Date : 2026-06-30 17:30
Source : agents/modifications.txt (30 juin 2026)
Produit par : agents/agent-brainstorm.md
Statut : prêt pour agent-dev

## 1. Résumé exécutif

Modifications issues de l'audit SQLite (`docs/audit-base-sqlite.md` §14 « Plan d'action recommandé »). L'utilisateur reprend la checklist de l'audit avec ses priorités P1→P4 et demande explicitement de ne pas implémenter le P4 (« optionnel / prématuré »). La ligne sur la redondance backend (`docs/audit_application.md`) est exclue — l'utilisateur l'a retirée du scope.

**P1 — Création de 3 nouvelles tables de persistance analytique + extension des best efforts + nettoyage d'une colonne redondante.** Objectif : supprimer les recalculs coûteux à chaque consultation d'activité (zones, splits, climbs) et enrichir les best efforts.

**P2 — Optimisations : cache, colonnes manquantes, agrégats journaliers, index.** Objectif : accélérer les endpoints d'analyse et de progression.

**P3 — Documentation, index marginaux, extraction FIT laps.** Objectif : compléter la couverture documentaire et les optimisations résiduelles.

**P4 — Explicitement exclu** par l'utilisateur (« optionnel / prématuré »).

**Tâche finale** : mise à jour de `docs/base-sqlite.md` pour refléter le nouveau schéma.

Au total : **13 actions P1-P3** + 1 mise à jour documentaire. Aucune modification frontend.

## 2. Demandes utilisateur extraites

### Demande 1 — Actions P1 (5 items)

- **Texte source** : checklist P1 dans `agents/modifications.txt`
- **Interprétation** : Créer 3 nouvelles tables (`progress_activity_zones`, `progress_activity_splits`, `progress_activity_climbs`) et les peupler via indexation lente. Étendre `progress_best_effort_points` aux efforts HR et power (`effort_kind`). Supprimer ou marquer `cardiac_drift_pct` comme alias de `decoupling_pct`.
- **Statut** : retenue
- **Justification** : Impact direct sur les performances — zones, splits et climbs sont actuellement recalculés à chaque `GET /activity/{id}/real`. Schémas déjà proposés dans l'audit §11.

### Demande 2 — Actions P2 (4 items)

- **Texte source** : checklist P2 dans `agents/modifications.txt`
- **Interprétation** : Activer `InMemoryCache` pour `/activity/{id}/real` (TTL 60s). Ajouter 8 colonnes à `progress_activity_index` (elevation_loss_m, pacing, puissance NP/IF/TSS, cadence). Créer `progress_daily_aggregates` pour `/progress/series` et `/progress/training-load`. Ajouter un index sur `activity_sources.activity_id`.
- **Statut** : retenue
- **Justification** : Optimisations à faible risque. Cache évite des recomputes, agrégats journaliers accélèrent les endpoints de progression.

### Demande 3 — Actions P3 (4 items)

- **Texte source** : checklist P3 dans `agents/modifications.txt`
- **Interprétation** : Documenter ~30 endpoints absents de `docs/metrics_catalog.md`. Ajouter index sur `progress_activity_index.activity_type` seul et sur `progress_activity_tags.source`. Implémenter extraction des laps Garmin depuis FIT.
- **Statut** : retenue
- **Justification** : Faible risque. Documentation et index marginaux. L'extraction FIT est la plus complexe mais reste P3.

### Demande 4 — Actions P4 (4 items)

- **Texte source** : checklist P4 + mention « optionnel / prématuré »
- **Statut** : rejetée (cette itération)
- **Justification** : L'utilisateur les qualifie lui-même de prématurés. À replanifier ultérieurement.

### Demande 5 — Mise à jour `docs/base-sqlite.md`

- **Texte source** : `A la fin : mettre à jour docs\base-sqlite.md`
- **Statut** : retenue
- **Justification** : Demande explicite. Le document est la référence technique du schéma et doit refléter les changements.

## 3. Diagnostic de l'existant

### 3.1 Fichiers et zones lus

- `docs/audit-base-sqlite.md` — audit complet (608 lignes), §14 plan d'action
- `docs/base-sqlite.md` — référence schéma SQLite (528 lignes)
- `docs/metrics_catalog.md` — catalogue endpoints API (484 lignes)
- `docs/indexation.md` — architecture indexation fast/slow
- `backend/db/models.py` — 11 modèles ORM (252 lignes)
- `backend/db/session.py` — migrations manuelles (94 lignes)
- `backend/db/progress_repository.py` — repository progression (296 lignes)
- `backend/progress/indexer.py` — `index_activity()` (462 lignes)
- `backend/progress/indexation_runner.py` — runner fast/slow (703 lignes)
- `backend/services/cache.py` — `InMemoryCache`, `MemoryCache` (169 lignes)
- `backend/core/real_run_analysis.py` — `compute_splits()`, `compute_climbs()`, `compute_best_efforts_by_duration()` (1551 lignes)
- `backend/core/metrics.py` — `compute_garmin_like_stats()`, `_build_zone_table()` (825 lignes)
- `backend/api/routes/analysis.py` — handler `get_real_activity`
- `backend/api/routes/progress.py` — routes progression (1074 lignes)

### 3.2 Constats établis

#### 3.2.1 `cardiac_drift_pct` = alias de `decoupling_pct`

- **Fait** : Dans `models.py:160-161`, les deux colonnes existent côte à côte.
- **Fait** : Dans `indexer.py:333-338`, `decoupling_pct = cardiac_drift_pct` (même valeur assignée aux deux).
- **Fait** : Aucun endpoint n'expose `cardiac_drift_pct` — seul `decoupling_pct` est dans `ProgressActivityRow`.
- **Conclusion** : Colonne redondante, suppression sans impact API.

#### 3.2.2 Tables manquantes

- **Fait** : Aucune des 4 nouvelles tables n'existe dans `models.py` ni dans la base.
- **Fait** : Zones calculées par `compute_garmin_like_stats()` → `_build_zone_table()`, recalculées à chaque consultation.
- **Fait** : Splits calculés par `compute_splits()` dans `real_run_analysis.py`, recalculés à chaque appel.
- **Fait** : Climbs calculés par `compute_climbs()`, retournent une liste de dicts.
- **Fait** : `compute_best_efforts_by_duration()` n'est appelée qu'avec le défaut (pace).

#### 3.2.3 Cache non utilisé

- **Fait** : `InMemoryCache` existe dans `services/cache.py` mais n'est pas instancié pour les endpoints d'analyse.
- **Fait** : `GET /activity/{id}/real` recharge le Parquet et recalcule tout à chaque appel.

#### 3.2.4 Colonnes manquantes

- **Fait** : `progress_activity_index` n'a pas `elevation_loss_m`, `pace_first_half_s_per_km`, `pace_second_half_s_per_km`, `power_normalized_w`, `power_intensity_factor`, `power_tss`, `cadence_mean_spm`, `cadence_max_spm`.
- **Fait** : Ces métriques sont calculées par `compute_garmin_like_stats()` mais non persistées.

#### 3.2.5 Index manquants

- `activity_sources` : pas d'index sur `activity_id` seul.
- `progress_activity_index` : pas d'index sur `activity_type` seul (seulement composite).
- `progress_activity_tags` : pas d'index sur `source`.

#### 3.2.6 Documentation

- `metrics_catalog.md` couvre ~33/39 endpoints. Manquent : CRUD activities/traces/goals, settings, Garmin, progress/index, training-load, calendar, geo, health, real-bins.

#### 3.2.7 Laps FIT

- Parsing FIT actuel ne supporte pas les messages `lap`. La lib `fitparse` le supporte.

### 3.3 Hypothèses

- `Base.metadata.create_all()` crée automatiquement les nouvelles tables.
- Les colonnes sont ajoutées via `ALTER TABLE ADD COLUMN` (pattern existant dans `session.py`).
- `compute_best_efforts_by_duration()` accepte un paramètre `metric` pour HR/power. Si non, adapter.
- Cache TTL 60s suffisant sans invalidation fine (changements HR max rares en usage local).
- `METRICS_VERSION` doit être incrémenté (6 → 7) pour forcer le recalcul.

### 3.4 Incertitudes

- Structure exacte du DataFrame zones : `range_low`/`range_high` séparés ou string `range` "X-Y" ? → inspecter `_build_zone_table()`.
- `compute_best_efforts_by_duration()` avec HR/power : testé ? → lire la fonction.
- Nombre exact de splits : estimé 10-40/activité.
- Nombre exact de climbs : estimé 0-10/activité.
- Complexité parsing FIT laps : variable selon appareils.

## 4. Spécification fonctionnelle cible

Après implémentation :

1. **Zones, splits, climbs** ne sont plus recalculés à chaque consultation. Calculés une fois lors de l'indexation lente, stockés, servis directement.
2. **Best efforts HR et power** disponibles dans `/progress/best-efforts` (`effort_kind=hr_bpm`, `effort_kind=power_w`).
3. **`/activity/{id}/real`** plus rapide grâce au cache TTL 60s.
4. **`/progress/series` et `/progress/training-load`** plus rapides grâce aux agrégats journaliers pré-calculés.
5. **Nouvelles métriques** dans `/progress/activities` : pacing, puissance avancée, cadence, dénivelé négatif.
6. **`cardiac_drift_pct`** n'existe plus dans le code.
7. **Documentation** à jour (`metrics_catalog.md` et `base-sqlite.md`).

### États à gérer

- **Absence de données** : colonnes puissance/cadence = NULL si pas de capteur. Tables zones/splits/climbs peuvent être vides.
- **Peuplement** : UNIQUEMENT via indexation lente. L'indexation rapide ne touche pas ces tables.
- **Rétrocompatibilité** : endpoints existants inchangés. Nouvelles tables peuplées en parallèle.
- **Migration** : colonnes ajoutées = NULL par défaut. Tables créées vides, peuplées au prochain passage d'indexation lente.

## 5. Spécification technique proposée

### 5.1 Modèles ORM — Nouvelles tables (P1)

Fichier : `backend/db/models.py`

#### 5.1.1 `ProgressActivityZone`

```python
class ProgressActivityZone(Base):
    __tablename__ = "progress_activity_zones"
    __table_args__ = (
        Index("ix_zones_activity_type", "activity_id", "zone_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'heart_rate', 'pace', 'power'
    zone_name: Mapped[str] = mapped_column(String(16), nullable=False)  # 'Z1', 'Z2', ...
    range_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    range_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_s: Mapped[float] = mapped_column(Float, nullable=False)
    time_pct: Mapped[float] = mapped_column(Float, nullable=False)
```

#### 5.1.2 `ProgressActivitySplit`

```python
class ProgressActivitySplit(Base):
    __tablename__ = "progress_activity_splits"
    __table_args__ = (
        Index("ix_splits_activity", "activity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    split_index: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    time_s: Mapped[float] = mapped_column(Float, nullable=False)
    pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, nullable=True)
```

#### 5.1.3 `ProgressActivityClimb`

```python
class ProgressActivityClimb(Base):
    __tablename__ = "progress_activity_climbs"
    __table_args__ = (
        Index("ix_climbs_activity", "activity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_gain_m: Mapped[float] = mapped_column(Float, nullable=False)
    avg_grade_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    vam_m_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
```

#### 5.1.4 `ProgressDailyAggregate` (P2)

```python
class ProgressDailyAggregate(Base):
    __tablename__ = "progress_daily_aggregates"

    date_utc: Mapped[str] = mapped_column(String(16), primary_key=True)  # YYYY-MM-DD
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    moving_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    elapsed_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    trimp: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    computed_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
```

### 5.2 Colonnes à ajouter à `ProgressActivityIndex` (P2)

Dans `models.py`, ajouter après les colonnes existantes de `ProgressActivityIndex` :

```python
elevation_loss_m: Mapped[float | None] = mapped_column(Float, nullable=True)
pace_first_half_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
pace_second_half_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
power_normalized_w: Mapped[float | None] = mapped_column(Float, nullable=True)
power_intensity_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
power_tss: Mapped[float | None] = mapped_column(Float, nullable=True)
cadence_mean_spm: Mapped[float | None] = mapped_column(Float, nullable=True)
cadence_max_spm: Mapped[float | None] = mapped_column(Float, nullable=True)
```

### 5.3 Suppression de `cardiac_drift_pct` (P1)

Dans `models.py`, supprimer la ligne :

```python
cardiac_drift_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
```

**Note SQLite** : `DROP COLUMN` supporté depuis SQLite 3.35.0 (mars 2021). Stratégie :
1. Supprimer du modèle ORM
2. Dans `session.py`, tenter `ALTER TABLE ... DROP COLUMN cardiac_drift_pct` avec try/except
3. La colonne physique peut persister dans d'anciennes bases — documenté dans `base-sqlite.md`

### 5.4 Nouveaux index (P2, P3)

Dans les `__table_args__` des classes existantes :

```python
# ActivitySource (P2)
Index("ix_activity_sources_activity_id", "activity_id"),

# ProgressActivityIndex (P3)
Index("ix_progress_activity_type", "activity_type"),

# ProgressActivityTag (P3)
Index("ix_progress_tags_source", "source"),
```

### 5.5 Migrations (`session.py`)

Dans `init_db()`, ajouter :

- **Nouvelles tables** : `Base.metadata.create_all()` les crée automatiquement.
- **Nouvelles colonnes** : 8 blocs `PRAGMA table_info(progress_activity_index)` + `ALTER TABLE ADD COLUMN` (pattern lignes 82-91 existantes).
- **Suppression `cardiac_drift_pct`** : `ALTER TABLE progress_activity_index DROP COLUMN cardiac_drift_pct` avec try/except.
- **Nouveaux index** : `CREATE INDEX IF NOT EXISTS` pour chaque index.

### 5.6 Nouvelles méthodes `ProgressRepository` (P1, P2)

Fichier : `backend/db/progress_repository.py`

```python
from .models import ProgressActivityZone, ProgressActivitySplit, ProgressActivityClimb, ProgressDailyAggregate

def replace_activity_zones(self, session, *, activity_id, zone_type, zones):
    session.execute(
        delete(ProgressActivityZone)
        .where(ProgressActivityZone.activity_id == activity_id)
        .where(ProgressActivityZone.zone_type == zone_type)
    )
    for z in zones:
        session.add(z)

def replace_activity_splits(self, session, *, activity_id, splits):
    session.execute(delete(ProgressActivitySplit).where(ProgressActivitySplit.activity_id == activity_id))
    for s in splits:
        session.add(s)

def replace_activity_climbs(self, session, *, activity_id, climbs):
    session.execute(delete(ProgressActivityClimb).where(ProgressActivityClimb.activity_id == activity_id))
    for c in climbs:
        session.add(c)

def upsert_daily_aggregate(self, session, *, row):
    existing = session.get(ProgressDailyAggregate, row.date_utc)
    if existing is None:
        session.add(row)
    else:
        for key, value in row.__dict__.items():
            if key.startswith("_"):
                continue
            setattr(existing, key, value)
```

### 5.7 Peuplement dans `indexer.py:index_activity()` (P1, P2)

Fichier : `backend/progress/indexer.py`

#### 5.7.1 Zones (P1)

Ajouter après le bloc best-efforts existant (~ligne 454) :

```python
# Zones HR, pace, power
zones_data = garmin.get("zones") if isinstance(garmin, dict) else None
if isinstance(zones_data, dict):
    for zone_type in ("heart_rate", "pace", "power"):
        zone_df = zones_data.get(zone_type)
        if zone_df is None:
            continue
        zone_rows = []
        if hasattr(zone_df, "iterrows"):
            for _, zrow in zone_df.iterrows():
                range_low = _finite_or_none(zrow.get("range_low")) if "range_low" in zone_df.columns else None
                range_high = _finite_or_none(zrow.get("range_high")) if "range_high" in zone_df.columns else None
                zone_rows.append(ProgressActivityZone(
                    activity_id=activity_id,
                    zone_type=str(zone_type),
                    zone_name=str(zrow.get("zone") or ""),
                    range_low=range_low,
                    range_high=range_high,
                    time_s=float(zrow.get("time_s") or 0),
                    time_pct=float(zrow.get("time_pct") or 0),
                ))
        repo.replace_activity_zones(session, activity_id=activity_id, zone_type=str(zone_type), zones=zone_rows)
```

**⚠️** : Inspecter `metrics.py:_build_zone_table()` avant — les colonnes peuvent être `range` (string "X-Y") au lieu de `range_low`/`range_high`.

#### 5.7.2 Splits (P1)

```python
from core.real_run_analysis import compute_splits

splits_df = compute_splits(df, total_distance_m=distance_m)
split_rows = []
if splits_df is not None and not splits_df.empty:
    for _, srow in splits_df.iterrows():
        split_rows.append(ProgressActivitySplit(
            activity_id=activity_id,
            split_index=int(srow.get("split_index") or 0),
            distance_km=float(srow.get("distance_km") or 0),
            time_s=float(srow.get("time_s") or 0),
            pace_s_per_km=_finite_or_none(srow.get("pace_s_per_km")),
            elevation_gain_m=_finite_or_none(srow.get("elevation_gain_m")),
        ))
repo.replace_activity_splits(session, activity_id=activity_id, splits=split_rows)
```

#### 5.7.3 Climbs (P1)

```python
from core.real_run_analysis import compute_climbs

climbs_list = compute_climbs(df)
climb_rows = []
if climbs_list:
    for c in climbs_list:
        if not isinstance(c, dict):
            continue
        climb_rows.append(ProgressActivityClimb(
            activity_id=activity_id,
            distance_km=float(c.get("distance_km") or 0),
            elevation_gain_m=float(c.get("elevation_gain_m") or 0),
            avg_grade_percent=_finite_or_none(c.get("avg_grade_percent")),
            pace_s_per_km=_finite_or_none(c.get("pace_s_per_km")),
            vam_m_h=_finite_or_none(c.get("vam_m_h")),
            start_km=_finite_or_none(c.get("start_km")),
            end_km=_finite_or_none(c.get("end_km")),
            duration_s=_finite_or_none(c.get("duration_s")),
        ))
repo.replace_activity_climbs(session, activity_id=activity_id, climbs=climb_rows)
```

#### 5.7.4 Best efforts HR et power (P1)

```python
# Best efforts HR
if has_hr:
    best_hr = compute_best_efforts_by_duration(df, durations_s=durations_s, metric="heart_rate")
    hr_points = []
    if best_hr is not None and not best_hr.empty:
        for _, r in best_hr.iterrows():
            dur = int(r.get("duration_s") or 0)
            val = _finite_or_none(r.get("heart_rate"))
            if dur <= 0 or val is None:
                continue
            hr_points.append(ProgressBestEffortPoint(
                activity_id=activity_id, start_ts_utc=start_ts_utc,
                effort_kind="hr_bpm", duration_s=dur, value=float(val),
            ))
    repo.replace_best_efforts(session, activity_id=activity_id, effort_kind="hr_bpm", points=hr_points)

# Best efforts power
if has_power:
    best_power = compute_best_efforts_by_duration(df, durations_s=durations_s, metric="power")
    power_points = []
    if best_power is not None and not best_power.empty:
        for _, r in best_power.iterrows():
            dur = int(r.get("duration_s") or 0)
            val = _finite_or_none(r.get("power"))
            if dur <= 0 or val is None:
                continue
            power_points.append(ProgressBestEffortPoint(
                activity_id=activity_id, start_ts_utc=start_ts_utc,
                effort_kind="power_w", duration_s=dur, value=float(val),
            ))
    repo.replace_best_efforts(session, activity_id=activity_id, effort_kind="power_w", points=power_points)
```

**⚠️** : Vérifier que `compute_best_efforts_by_duration()` accepte `metric="heart_rate"` et `metric="power"`. Si non, adapter la fonction.

#### 5.7.5 Nettoyage `cardiac_drift_pct` (P1)

Dans `index_activity()`, supprimer la variable locale `cardiac_drift_pct` et l'assignation dans le constructeur. Renommer directement :

```python
decoupling_pct = _finite_or_none(pacing.get("cardiac_drift_pct"))
```

Ne garder que `decoupling_pct=decoupling_pct` dans le constructeur `ProgressActivityIndex(...)`.

#### 5.7.6 Nouvelles colonnes `progress_activity_index` (P2)

Extraire après les métriques existantes dans `index_activity()` :

```python
elevation_loss_m = _finite_or_none(summary.get("elevation_loss_m"))
pace_first_half = _finite_or_none(pacing.get("pace_first_half_s_per_km"))
pace_second_half = _finite_or_none(pacing.get("pace_second_half_s_per_km"))

power_data = garmin.get("power_advanced") if isinstance(garmin, dict) else None
power_np = _finite_or_none(power_data.get("normalized_power_w")) if isinstance(power_data, dict) else None
power_if = _finite_or_none(power_data.get("intensity_factor")) if isinstance(power_data, dict) else None
power_tss_val = _finite_or_none(power_data.get("tss")) if isinstance(power_data, dict) else None

cadence_data = garmin.get("cadence") if isinstance(garmin, dict) else None
cadence_mean = _finite_or_none(cadence_data.get("mean_spm")) if isinstance(cadence_data, dict) else None
cadence_max = _finite_or_none(cadence_data.get("max_spm")) if isinstance(cadence_data, dict) else None
```

Ajouter ces variables dans les kwargs du constructeur `ProgressActivityIndex(...)`.

### 5.8 Agrégats journaliers (P2)

Dans `backend/progress/indexer.py` (ou nouveau `backend/progress/daily_aggregator.py`) :

```python
def recompute_daily_aggregates(session: Session) -> None:
    from db.models import ProgressDailyAggregate, utc_now_iso
    from sqlalchemy import func

    repo = ProgressRepository()
    stmt = (
        select(
            func.substr(ProgressActivityIndex.start_ts_utc, 1, 10).label("date_utc"),
            func.sum(ProgressActivityIndex.distance_m).label("distance_m"),
            func.sum(ProgressActivityIndex.moving_time_s).label("moving_time_s"),
            func.sum(ProgressActivityIndex.elapsed_time_s).label("elapsed_time_s"),
            func.sum(ProgressActivityIndex.elevation_gain_m).label("elevation_gain_m"),
            func.sum(ProgressActivityIndex.trimp).label("trimp"),
            func.count(ProgressActivityIndex.activity_id).label("activity_count"),
        )
        .where(ProgressActivityIndex.activity_type == "real")
        .group_by(func.substr(ProgressActivityIndex.start_ts_utc, 1, 10))
    )
    rows = session.execute(stmt).all()
    now = utc_now_iso()
    for r in rows:
        repo.upsert_daily_aggregate(session, row=ProgressDailyAggregate(
            date_utc=str(r.date_utc),
            distance_m=float(r.distance_m) if r.distance_m else None,
            moving_time_s=float(r.moving_time_s) if r.moving_time_s else None,
            elapsed_time_s=float(r.elapsed_time_s) if r.elapsed_time_s else None,
            elevation_gain_m=float(r.elevation_gain_m) if r.elevation_gain_m else None,
            trimp=float(r.trimp) if r.trimp else None,
            activity_count=int(r.activity_count or 0),
            computed_at_utc=now,
        ))
```

Appeler `recompute_daily_aggregates(session)` à la fin de l'indexation lente (dans `indexation_runner.py`, phase post-processing).

### 5.9 Cache `InMemoryCache` pour `/activity/{id}/real` (P2)

Fichier : `backend/api/routes/analysis.py`

```python
from services.cache import InMemoryCache, make_cache_key

real_activity_cache = InMemoryCache(max_items=256)
CACHE_VERSION = "2"

@router.get("/activity/{id}/real")
async def get_real_activity(request: Request, id: str):
    # ... code existant pour récupérer settings, etc.
    
    # Cache
    hr_max = ...  # hr max effectif (détecté ou manuel)
    cache_key = make_cache_key(
        namespace="real_activity",
        version=CACHE_VERSION,
        payload={"activity_id": id, "hr_max": hr_max},
    )
    cached = real_activity_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # ... calcul existant
    result = ...
    real_activity_cache.set(cache_key, result, ttl_s=60)
    return result
```

### 5.10 Documentation `metrics_catalog.md` (P3)

Ajouter les sections pour les endpoints non documentés (audit §3.2) :
- CRUD activities, traces, goals
- Settings (GET, PATCH, hr-max-detected)
- Garmin (6 endpoints)
- Progress/index (fast, slow, status), training-load, calendar
- Geo/cities, `/`, `/health`, real-bins

Format : tableaux markdown avec Path, Type, Unit, Description — cohérent avec l'existant.

### 5.11 Extraction laps Garmin FIT (P3)

- **Fichier** : `backend/core/parsing/` — parser les messages `lap` FIT
- **Table optionnelle** : `activity_laps` (modèle fourni en annexe si nécessaire)
- **Peuplement** : dans `indexer.py`, lors de l'indexation lente

Si la complexité est trop élevée, limiter à l'extraction sans créer la table.

### 5.12 Mise à jour `docs/base-sqlite.md` (tâche finale)

Mettre à jour les sections :
- §2 : ajouter les 4 nouvelles tables
- §2.8.1 : documenter les 8 nouvelles colonnes
- §2.8.2 : documenter les nouveaux `effort_kind`
- §4 : noter la suppression de `cardiac_drift_pct`
- §6 : ajouter les nouvelles migrations
- §12 : ajouter les nouveaux index

## 6. Plan d'implémentation pour agent-dev

**Ordre** : P1 (étapes 1-5, parallélisables) → P2 (6-10) → P3 (11-13) → Tâche finale (14).

### Étape 1 — P1 : Modèles ORM pour les 3 nouvelles tables

- **Fichier** : `backend/db/models.py`
- **Action** : Ajouter `ProgressActivityZone`, `ProgressActivitySplit`, `ProgressActivityClimb`
- **Vérification** : `python -m compileall backend`

### Étape 2 — P1 : Nouvelles méthodes `ProgressRepository`

- **Fichier** : `backend/db/progress_repository.py`
- **Action** : Ajouter `replace_activity_zones()`, `replace_activity_splits()`, `replace_activity_climbs()`
- **Vérification** : `python -m compileall backend`

### Étape 3 — P1 : Peuplement zones, splits, climbs dans `index_activity()`

- **Fichier** : `backend/progress/indexer.py`
- **Action** : Ajouter extraction et persistance (cf. §5.7.1-5.7.3). Incrémenter `METRICS_VERSION` (6 → 7).
- **⚠️** : Inspecter `_build_zone_table()`, `compute_splits()`, `compute_climbs()` avant le mapping.
- **Vérification** : `python -m compileall backend`, indexation lente, `SELECT COUNT(*)` sur les nouvelles tables.

### Étape 4 — P1 : Best efforts HR et power

- **Fichier** : `backend/progress/indexer.py`
- **Action** : Ajouter §5.7.4. Vérifier `compute_best_efforts_by_duration()` avant.
- **Vérification** : `SELECT DISTINCT effort_kind FROM progress_best_effort_points`

### Étape 5 — P1 : Supprimer `cardiac_drift_pct`

- **Fichiers** : `backend/db/models.py`, `backend/db/session.py`, `backend/progress/indexer.py`
- **Action** : Supprimer colonne du modèle. Tenter `DROP COLUMN` dans `session.py`. Nettoyer `indexer.py` (cf. §5.7.5).
- **⚠️** : `grep -r cardiac_drift_pct backend/` pour vérifier l'absence de références.
- **Vérification** : `python -m compileall backend`

### Étape 6 — P2 : Modèle + repo `ProgressDailyAggregate`

- **Fichiers** : `backend/db/models.py`, `backend/db/progress_repository.py`
- **Action** : Ajouter modèle et `upsert_daily_aggregate()`
- **Vérification** : `python -m compileall backend`

### Étape 7 — P2 : `recompute_daily_aggregates()` + appel dans le runner

- **Fichiers** : `backend/progress/indexer.py` (ou `daily_aggregator.py`), `backend/progress/indexation_runner.py`
- **Action** : Implémenter §5.8. Appeler en fin d'indexation lente.
- **Vérification** : Indexation lente, `SELECT * FROM progress_daily_aggregates`

### Étape 8 — P2 : Cache `InMemoryCache` pour `/activity/{id}/real`

- **Fichier** : `backend/api/routes/analysis.py`
- **Action** : Implémenter §5.9.
- **Vérification** : 2 appels < 60s, second plus rapide.

### Étape 9 — P2 : Ajouter 8 colonnes à `progress_activity_index`

- **Fichiers** : `backend/db/models.py`, `backend/db/session.py` (migrations), `backend/progress/indexer.py` (peuplement)
- **Action** : Colonnes au modèle. Migrations `ALTER TABLE ADD COLUMN`. Extraction dans `index_activity()` (cf. §5.7.6).
- **⚠️** : Vérifier les clés exactes dans le dict `compute_garmin_like_stats()`.
- **Vérification** : `PRAGMA table_info(progress_activity_index)`, indexation lente.

### Étape 10 — P2 : Index `activity_sources.activity_id`

- **Fichiers** : `backend/db/models.py`, `backend/db/session.py`
- **Action** : `Index(...)` + `CREATE INDEX IF NOT EXISTS`
- **Vérification** : `PRAGMA index_list('activity_sources')`

### Étape 11 — P3 : Index `progress_activity_index.activity_type` et `progress_activity_tags.source`

- **Fichiers** : `backend/db/models.py`, `backend/db/session.py`
- **Action** : Même pattern que l'étape 10.
- **Vérification** : `PRAGMA index_list()` sur chaque table.

### Étape 12 — P3 : Documenter endpoints dans `metrics_catalog.md`

- **Fichier** : `docs/metrics_catalog.md`
- **Action** : Ajouter sections pour ~30 endpoints manquants.
- **Vérification** : Relecture manuelle.

### Étape 13 — P3 : Extraction laps Garmin FIT

- **Fichier** : `backend/core/parsing/` (+ optionnellement `models.py`, `indexer.py`)
- **Action** : Parser les messages `lap`. Table `activity_laps` optionnelle.
- **⚠️** : Si trop complexe, limiter à l'extraction sans persistance.

### Étape 14 — Tâche finale : `docs/base-sqlite.md`

- **Fichier** : `docs/base-sqlite.md`
- **Action** : Mettre à jour §2, §2.8.1, §2.8.2, §4, §6, §12.

## 7. Tests et vérifications attendus

### Backend

```bash
python -m compileall backend
python -m pytest tests/unit/ -x -q
python -m pytest tests/pytest/ -x -q
```

Vérifications sqlite3 :

```bash
sqlite3 data/coursescope.sqlite ".tables"
sqlite3 data/coursescope.sqlite "PRAGMA table_info(progress_activity_index)"
sqlite3 data/coursescope.sqlite "SELECT DISTINCT effort_kind FROM progress_best_effort_points"
sqlite3 data/coursescope.sqlite "SELECT COUNT(*) FROM progress_activity_zones"
sqlite3 data/coursescope.sqlite "SELECT COUNT(*) FROM progress_activity_splits"
sqlite3 data/coursescope.sqlite "SELECT COUNT(*) FROM progress_activity_climbs"
sqlite3 data/coursescope.sqlite "SELECT COUNT(*) FROM progress_daily_aggregates"
```

### Frontend

```bash
cd frontend && npm run build
```

## 8. Critères d'acceptation

- [ ] `progress_activity_zones` créée et peuplée (HR, pace, power par activité)
- [ ] `progress_activity_splits` créée et peuplée
- [ ] `progress_activity_climbs` créée et peuplée
- [ ] `progress_best_effort_points` contient `effort_kind IN ('pace_s_per_km', 'hr_bpm', 'power_w')`
- [ ] `cardiac_drift_pct` n'est plus référencé dans le code
- [ ] `InMemoryCache` actif pour `/activity/{id}/real` (TTL 60s)
- [ ] `progress_activity_index` a 8 nouvelles colonnes
- [ ] `progress_daily_aggregates` créée et peuplée
- [ ] Index `activity_sources.activity_id` présent
- [ ] Index `progress_activity_index.activity_type` présent
- [ ] Index `progress_activity_tags.source` présent
- [ ] `docs/metrics_catalog.md` documente les endpoints manquants
- [ ] `docs/base-sqlite.md` reflète le nouveau schéma
- [ ] `python -m compileall backend` passe
- [ ] `python -m pytest tests/unit/ -x -q` passe
- [ ] `cd frontend && npm run build` passe
- [ ] Aucune régression sur les endpoints existants
- [ ] `METRICS_VERSION` incrémenté à 7

## 9. Risques et garde-fous

### Risque 1 — Structure du DataFrame zones inconnue
**Garde-fou** : Inspecter `_build_zone_table()` avant d'écrire le mapping. Les colonnes peuvent être `range` (string) au lieu de `range_low`/`range_high`.

### Risque 2 — `compute_best_efforts_by_duration()` sans support HR/power
**Garde-fou** : Lire la fonction. Si le paramètre `metric` n'existe pas, implémenter une approche alternative (rolling sur fenêtres).

### Risque 3 — Régressions dans l'indexation lente
**Garde-fou** : Wrapper chaque nouveau bloc dans try/except. Une activité qui échoue ne bloque pas les autres.

### Risque 4 — Cache invalidation
**Garde-fou** : Clé inclut HR max effectif + TTL 60s. Suffisant pour usage local mono-utilisateur.

### Risque 5 — Migration SQLite < 3.35
**Garde-fou** : Toutes les migrations en try/except silencieux (pattern `session.py`). `DROP COLUMN` tenté avec fallback.

### Risque 6 — Volume d'indexation lente
**Garde-fou** : +2-5s/activité estimé. Background thread, pas de blocage UI. `METRICS_VERSION=7` force un seul recalcul complet.

### Risque 7 — `METRICS_VERSION` et recalcul forcé
**Garde-fou** : Incrément garantit le peuplement de toutes les nouvelles tables pour toutes les activités existantes.

## 10. Décisions prises par agent-brainstorm

1. **`cardiac_drift_pct` supprimé du modèle ORM** — colonne physique laissée si SQLite < 3.35. Documenté.
2. **`METRICS_VERSION` 6 → 7** — force recalcul complet au prochain passage d'indexation lente.
3. **Zones stockées par type** — une ligne par zone, filtrable via `zone_type`.
4. **Peuplement UNIQUEMENT via indexation lente** — cohérent avec fast/slow.
5. **Cache TTL 60s sans invalidation fine** — compromis acceptable pour usage local.
6. **P4 non implémenté** — conforme à la demande utilisateur.
7. **Extraction FIT laps limitée au parsing** — table `activity_laps` optionnelle si complexe.
8. **Ordre P1 → P2 → P3 → final** — items P1 parallélisables entre eux.

## 11. Points à ne pas faire

- **Ne pas modifier les endpoints API existants** — contrats inchangés.
- **Ne pas toucher `progress_pace_hr_bins`** — hors scope.
- **Ne pas modifier le frontend** — aucune modification UI.
- **Ne pas implémenter P4** — pipeline, Redis, normalisation, gear.
- **Ne pas faire de refactoring lourd** (`real_run_analysis.py`, `progress/page.tsx`).
- **Ne pas modifier `agents/modifications.txt`**.
- **Ne pas modifier `docs/audit_application.md`** ni traiter la redondance backend.
- **Ne pas changer `effort_kind='pace_s_per_km'` existant**.
- **Ne pas modifier l'indexation rapide** — elle reste strictement structurelle.
