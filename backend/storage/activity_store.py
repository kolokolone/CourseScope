from abc import ABC, abstractmethod
from typing import Callable, List
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid
import hashlib
import shutil
import logging

import pandas as pd

from api.schemas import ActivityMetadata, SidebarStats
from core.stats.basic_stats import compute_basic_stats
from progress._utils import _parse_iso_datetime, _to_utc, _infer_started_at_utc_from_df
from services.models import LoadedActivity as ServiceLoadedActivity
from db.repository import ActivityIndexRepository


logger = logging.getLogger("coursescope")


def _model_to_dict(model):
    if hasattr(model, "model_dump"):
        # Pydantic v2: ensure JSON-compatible types (datetime -> ISO string).
        return model.model_dump(mode="json")
    if hasattr(model, "json"):
        # Pydantic v1 fallback.
        return json.loads(model.json())
    return model.dict()


class ActivityStorage(ABC):
    @abstractmethod
    def store(self, activity: ServiceLoadedActivity, filename: str, raw_bytes: bytes, name: str | None = None) -> str:
        """Stocke activité, retourne ID"""
        pass

    @abstractmethod
    def load(self, activity_id: str) -> ServiceLoadedActivity:
        """Charge activité par ID"""
        pass

    @abstractmethod
    def load_dataframe(self, activity_id: str) -> pd.DataFrame:
        """Charge DataFrame par ID (lazy loading)"""
        pass

    @abstractmethod
    def list_activities(self) -> List[ActivityMetadata]:
        """Liste toutes activités stockées"""
        pass

    @abstractmethod
    def delete(self, activity_id: str) -> bool:
        """Supprime activité"""
        pass

    @abstractmethod
    def cleanup_all(self) -> None:
        """Supprime toutes les activités"""
        pass

    @abstractmethod
    def get_activity_payload(self, activity_id: str) -> dict:
        """Retourne filename/name/raw_bytes/df pour un activity_id."""
        pass

    @abstractmethod
    def rename_activity(self, activity_id: str, name: str | None) -> bool:
        """Renomme une activité stockée."""
        pass


class LocalTempStorage(ActivityStorage):
    """Stockage local dans dossier persistant"""

    def __init__(
        self,
        temp_dir: str = "./data/activities",
        db_session_factory: Callable[[], object] | None = None,
    ):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._db_session_factory = db_session_factory
        self._repo = ActivityIndexRepository() if db_session_factory is not None else None

    def _get_extension(self, filename: str) -> str:
        """Extrait l'extension du fichier"""
        return Path(filename).suffix.lower().lstrip(".")

    def _hash_bytes(self, data: bytes) -> str:
        """Calcule SHA256 pour déduplication"""
        return hashlib.sha256(data).hexdigest()

    def get_activity_id_by_hash(self, file_hash_sha256: str) -> str | None:
        """Return activity id if a file hash already exists.

        Note: only works when the DB index is enabled.
        """

        return self._get_db_activity_id_by_hash(file_hash_sha256)

    def _get_db_activity_id_by_hash(self, file_hash: str) -> str | None:
        if self._db_session_factory is None or self._repo is None:
            return None
        session = self._db_session_factory()
        try:
            # Session type is runtime-provided (SQLAlchemy Session).
            activity_id = self._repo.get_activity_id_by_hash(session, file_hash)  # type: ignore[arg-type]
            if activity_id is not None and not self._get_activity_dir(activity_id).exists():
                return None
            return activity_id
        finally:
            try:
                session.close()  # type: ignore[attr-defined]
            except Exception:
                pass

    def _infer_started_at_utc(self, df: pd.DataFrame) -> str | None:
        return _infer_started_at_utc_from_df(df)

    def _get_activity_dir(self, activity_id: str) -> Path:
        """Retourne le chemin du dossier d'activité"""
        return self.temp_dir / activity_id

    def _compute_sidebar_stats(self, df: pd.DataFrame) -> SidebarStats:
        """Calcule statistiques sidebar depuis DataFrame"""
        if df.empty:
            return SidebarStats()

        moving_mask = None
        if "speed_m_s" in df.columns:
            moving_mask = df["speed_m_s"] > 0.5

        stats = compute_basic_stats(df, moving_mask=moving_mask)
        return SidebarStats(
            distance_km=stats.distance_km if stats.distance_km > 0 else None,
            elapsed_time_s=stats.total_time_s if stats.total_time_s > 0 else None,
            moving_time_s=stats.moving_time_s if stats.moving_time_s > 0 else None,
            elevation_gain_m=stats.elevation_gain_m if stats.elevation_gain_m > 0 else None,
        )

    def store(self, activity: ServiceLoadedActivity, filename: str, raw_bytes: bytes, name: str | None = None) -> str:
        """Stocke activité avec UUID unique.

        Déduplication:
        - Si un index DB est configuré, utilise file_hash_sha256 (raw bytes) pour éviter les doublons.
        """

        file_hash = self._hash_bytes(raw_bytes)
        existing_id = self._get_db_activity_id_by_hash(file_hash)
        if existing_id is not None:
            return existing_id

        activity_id = str(uuid.uuid4())
        activity_dir = self._get_activity_dir(activity_id)
        activity_dir.mkdir(exist_ok=True)

        try:
            file_path = activity_dir / f"original.{self._get_extension(filename)}"
            with open(file_path, "wb") as f:
                f.write(raw_bytes)

            df = activity.df
            if df is None:
                raise RuntimeError("Loaded activity is missing DataFrame data")

            df_path = activity_dir / "df.parquet"
            df_to_store = df.copy()
            for column in df_to_store.columns:
                if isinstance(df_to_store[column].dtype, pd.DatetimeTZDtype):
                    df_to_store[column] = df_to_store[column].dt.tz_convert("UTC").dt.tz_localize(None)
            logger.info(
                "store_parquet_start",
                extra={
                    "request_id": "-",
                    "activity_id": activity_id,
                    "rows": int(df_to_store.shape[0]),
                    "cols": int(df_to_store.shape[1]),
                },
            )
            df_to_store.to_parquet(df_path, engine="pyarrow")
            logger.info(
                "store_parquet_ok",
                extra={
                    "request_id": "-",
                    "activity_id": activity_id,
                    "path": str(df_path),
                },
            )

            activity_type = "real" if activity.gpx_type.type == "real_run" else "theoretical"

            started_at_utc = self._infer_started_at_utc(df)
            created_at_dt = datetime.now(timezone.utc).replace(microsecond=0)
            started_at_dt = _parse_iso_datetime(started_at_utc) if started_at_utc else None
            if started_at_dt is not None:
                started_at_dt = _to_utc(started_at_dt)
            created_at_utc = _to_utc(created_at_dt).isoformat().replace("+00:00", "Z")

            metadata = ActivityMetadata(
                id=activity_id,
                filename=filename,
                name=name,
                activity_type=activity_type,
                created_at=created_at_dt,
                started_at=started_at_dt,
                stats_sidebar=self._compute_sidebar_stats(df),
                file_hash=file_hash,
            )

            meta_path = activity_dir / "meta.json"
            with open(meta_path, "w") as f:
                json.dump(_model_to_dict(metadata), f, default=str, indent=2)

            if self._db_session_factory is not None and self._repo is not None:
                session = self._db_session_factory()
                try:
                    self._repo.create_activity(
                        session,  # type: ignore[arg-type]
                        activity_id=activity_id,
                        name=name,
                        activity_type=activity_type,
                        started_at_utc=started_at_utc,
                        created_at_utc=created_at_utc,
                        file_hash_sha256=file_hash,
                        original_path=str(file_path.resolve()),
                        parquet_path=str(df_path.resolve()),
                    )
                    session.commit()  # type: ignore[attr-defined]
                except Exception:
                    try:
                        session.rollback()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    raise
                finally:
                    try:
                        session.close()  # type: ignore[attr-defined]
                    except Exception:
                        pass

            # Best-effort: update the analytical progress index.
            # Keep uploads/sync functional even if indexing fails.
            if self._db_session_factory is not None:
                meta_dict = _model_to_dict(metadata)
                session = self._db_session_factory()
                try:
                    from progress.indexer import index_activity

                    index_activity(
                        session, activity_id=activity_id, df=df_to_store, meta=meta_dict, parquet_path=df_path
                    )
                    session.commit()  # type: ignore[attr-defined]
                except Exception as exc:
                    try:
                        session.rollback()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    logger.warning(
                        "progress_index_failed",
                        extra={
                            "request_id": "-",
                            "activity_id": activity_id,
                            "error": str(exc),
                        },
                    )
                finally:
                    try:
                        session.close()  # type: ignore[attr-defined]
                    except Exception:
                        pass

            return activity_id

        except Exception as e:
            if activity_dir.exists():
                shutil.rmtree(activity_dir)
            raise RuntimeError(f"Failed to store activity: {e}")

    def load(self, activity_id: str) -> ServiceLoadedActivity:
        """Charge activité complète (lazy loading DataFrame)"""
        activity_dir = self._get_activity_dir(activity_id)

        if not activity_dir.exists():
            raise FileNotFoundError(f"Activity {activity_id} not found")

        meta_path = activity_dir / "meta.json"
        with open(meta_path, "r") as f:
            metadata = json.load(f)

        from services.models import ActivityTypeDetection

        activity_type = "real_run" if metadata["activity_type"] == "real" else "theoretical_route"
        gpx_type = ActivityTypeDetection(type=activity_type, confidence=1.0)

        return ServiceLoadedActivity(
            name=metadata.get("name") or metadata["filename"],
            df=None,
            gpx_type=gpx_type,
            track_count=1,
        )

    def load_dataframe(self, activity_id: str) -> pd.DataFrame:
        """Charge DataFrame pour lazy loading"""
        activity_dir = self._get_activity_dir(activity_id)
        df_path = activity_dir / "df.parquet"

        if not df_path.exists():
            raise FileNotFoundError(f"DataFrame for activity {activity_id} not found")

        return pd.read_parquet(df_path)

    def list_activities(self) -> List[ActivityMetadata]:
        """Liste toutes les métadonnées"""
        activities: list[ActivityMetadata] = []

        if not self.temp_dir.exists():
            return activities

        for activity_dir in self.temp_dir.iterdir():
            if not activity_dir.is_dir():
                continue

            meta_path = activity_dir / "meta.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r") as f:
                        metadata_dict = json.load(f)

                    created_at = _parse_iso_datetime(metadata_dict.get("created_at"))
                    if created_at is not None:
                        metadata_dict["created_at"] = _to_utc(created_at)
                    started_at = _parse_iso_datetime(metadata_dict.get("started_at"))
                    if started_at is not None:
                        metadata_dict["started_at"] = _to_utc(started_at)
                    else:
                        # Backfill for legacy meta.json (derive from df.parquet without rewriting).
                        df_path = activity_dir / "df.parquet"
                        try:
                            if df_path.exists():
                                df_time = pd.read_parquet(df_path, columns=["time"])
                                if not df_time.empty and "time" in df_time.columns:
                                    v = df_time["time"].min()
                                    if v is not None:
                                        is_na = pd.isna(v)
                                        if bool(is_na):
                                            continue
                                        started_guess = pd.to_datetime(v).to_pydatetime()
                                        metadata_dict["started_at"] = _to_utc(started_guess)
                        except Exception:
                            pass

                    activities.append(ActivityMetadata(**metadata_dict))
                except Exception as e:
                    logger.warning(
                        "metadata_load_failed",
                        extra={
                            "request_id": "-",
                            "activity_id": activity_dir.name,
                            "error": str(e),
                        },
                    )
                    continue

        activities.sort(
            key=lambda a: (a.started_at or a.created_at),
            reverse=True,
        )
        return activities

    def delete(self, activity_id: str) -> bool:
        """Supprime une activité spécifique"""
        activity_dir = self._get_activity_dir(activity_id)

        if not activity_dir.exists():
            return False

        try:
            shutil.rmtree(activity_dir)
            return True
        except Exception:
            return False

    def cleanup_all(self) -> None:
        """Suppression complète dossier"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_activity_payload(self, activity_id: str) -> dict:
        activity_dir = self._get_activity_dir(activity_id)
        if not activity_dir.exists():
            raise FileNotFoundError(f"Activity {activity_id} not found")

        meta_path = activity_dir / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata for activity {activity_id} not found")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        original_path = None
        for p in activity_dir.iterdir():
            if p.is_file() and p.name.startswith("original"):
                original_path = p
                break
        if original_path is None:
            raise FileNotFoundError(f"Original file for activity {activity_id} not found")

        df = self.load_dataframe(activity_id)
        return {
            "filename": meta.get("filename") or original_path.name,
            "name": meta.get("name"),
            "raw_bytes": original_path.read_bytes(),
            "df": df,
        }

    def rename_activity(self, activity_id: str, name: str | None) -> bool:
        activity_dir = self._get_activity_dir(activity_id)
        if not activity_dir.exists():
            return False

        meta_path = activity_dir / "meta.json"
        if not meta_path.exists():
            return False

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        cleaned_name = str(name).strip() if isinstance(name, str) else ""
        meta["name"] = cleaned_name if cleaned_name else None

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, default=str, indent=2)

        if self._db_session_factory is not None and self._repo is not None:
            session = self._db_session_factory()
            try:
                self._repo.rename_activity(session, activity_id, meta["name"])  # type: ignore[arg-type]
                session.commit()  # type: ignore[attr-defined]
            except Exception:
                try:
                    session.rollback()  # type: ignore[attr-defined]
                except Exception:
                    pass
                raise
            finally:
                try:
                    session.close()  # type: ignore[attr-defined]
                except Exception:
                    pass

        return True


class InMemoryStorage(ActivityStorage):
    """Ephemeral storage (process memory only)."""

    def __init__(self):
        self._dataframes: dict[str, pd.DataFrame] = {}
        self._metas: dict[str, dict] = {}
        self._raw_bytes: dict[str, bytes] = {}

    def store(self, activity: ServiceLoadedActivity, filename: str, raw_bytes: bytes, name: str | None = None) -> str:
        df = activity.df
        if df is None:
            raise RuntimeError("Loaded activity is missing DataFrame data")

        activity_id = str(uuid.uuid4())
        self._dataframes[activity_id] = df
        self._metas[activity_id] = {
            "id": activity_id,
            "filename": filename,
            "name": name,
            "created_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        }
        self._raw_bytes[activity_id] = bytes(raw_bytes)
        return activity_id

    def load(self, activity_id: str) -> ServiceLoadedActivity:
        meta = self._metas.get(activity_id)
        if meta is None:
            raise FileNotFoundError(f"Activity {activity_id} not found")

        from services.models import ActivityTypeDetection

        gpx_type = ActivityTypeDetection(type="real_run", confidence=1.0)
        return ServiceLoadedActivity(
            name=meta.get("name") or meta.get("filename") or activity_id,
            df=None,
            gpx_type=gpx_type,
            track_count=1,
        )

    def load_dataframe(self, activity_id: str) -> pd.DataFrame:
        df = self._dataframes.get(activity_id)
        if df is None:
            raise FileNotFoundError(f"Activity {activity_id} not found")
        return df

    def list_activities(self) -> List[ActivityMetadata]:
        return []

    def delete(self, activity_id: str) -> bool:
        existed = activity_id in self._dataframes
        self._dataframes.pop(activity_id, None)
        self._metas.pop(activity_id, None)
        return existed

    def cleanup_all(self) -> None:
        self._dataframes.clear()
        self._metas.clear()
        self._raw_bytes.clear()

    def get_activity_payload(self, activity_id: str) -> dict:
        df = self._dataframes.get(activity_id)
        meta = self._metas.get(activity_id)
        raw = self._raw_bytes.get(activity_id)
        if df is None or meta is None or raw is None:
            raise FileNotFoundError(f"Activity {activity_id} not found")
        return {
            "filename": meta.get("filename") or f"{activity_id}.gpx",
            "name": meta.get("name"),
            "raw_bytes": bytes(raw),
            "df": df,
        }

    def rename_activity(self, activity_id: str, name: str | None) -> bool:
        meta = self._metas.get(activity_id)
        if meta is None:
            return False
        cleaned_name = str(name).strip() if isinstance(name, str) else ""
        meta["name"] = cleaned_name if cleaned_name else None
        return True
