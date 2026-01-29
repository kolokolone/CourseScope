from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from pathlib import Path
import json
import uuid
import hashlib
import shutil

import pandas as pd

from api.schemas import ActivityMetadata, SidebarStats
from core.stats.basic_stats import compute_basic_stats
from services.models import LoadedActivity as ServiceLoadedActivity


def _model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
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


class LocalTempStorage(ActivityStorage):
    """Stockage local dans dossier persistant"""

    def __init__(self, temp_dir: str = "./data/activities"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _get_extension(self, filename: str) -> str:
        """Extrait l'extension du fichier"""
        return Path(filename).suffix.lower().lstrip(".")

    def _hash_bytes(self, data: bytes) -> str:
        """Calcule SHA256 pour déduplication"""
        return hashlib.sha256(data).hexdigest()

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
        """Stocke activité avec UUID unique"""
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
            df_to_store.to_parquet(df_path)

            activity_type = "real" if activity.gpx_type.type == "real_run" else "theoretical"

            metadata = ActivityMetadata(
                id=activity_id,
                filename=filename,
                name=name,
                activity_type=activity_type,
                created_at=datetime.now(),
                stats_sidebar=self._compute_sidebar_stats(df),
                file_hash=self._hash_bytes(raw_bytes),
            )

            meta_path = activity_dir / "meta.json"
            with open(meta_path, "w") as f:
                json.dump(_model_to_dict(metadata), f, default=str, indent=2)

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
        activities = []

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

                    metadata_dict["created_at"] = datetime.fromisoformat(
                        metadata_dict["created_at"].replace("Z", "+00:00")
                    )

                    activities.append(ActivityMetadata(**metadata_dict))
                except Exception as e:
                    print(f"Warning: Failed to load metadata for {activity_dir.name}: {e}")
                    continue

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
