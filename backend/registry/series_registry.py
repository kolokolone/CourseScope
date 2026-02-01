from dataclasses import dataclass
from typing import List, Literal, Optional, Callable, Dict, Any, cast
import pandas as pd
import numpy as np

from api.schemas import SeriesInfo, SeriesResponse, SeriesMeta
from core.constants import DEFAULT_GRADE_SMOOTH_WINDOW
from core.real_run_analysis import compute_grade_percent_series, compute_moving_mask


@dataclass
class SeriesDefinition:
    name: str
    unit: str
    x_axes: List[Literal["time", "distance"]]
    default: bool
    source_column: Optional[str] = None  # Colonnes directes du DataFrame
    compute_func: Optional[Callable] = None  # Fonction calcul dérivé
    requires_params: Optional[Dict[str, Any]] = None  # Paramètres calcul


class DownsamplingStrategy:
    """Algorithmes downsampling par type de série"""
    
    @staticmethod
    def lttb_downsample(x, y, target_points: int):
        """Largest-Triangle-Three-Buckets - préserve features"""
        if len(x) <= target_points:
            return x, y
            
        # Simplification : échantillonnage uniforme pour MVP
        # TODO: implémenter vrai LTTB plus tard
        step = max(1, len(x) // target_points)
        indices = np.arange(0, len(x), step)
        
        return x[indices], y[indices]
    
    @staticmethod  
    def uniform_downsample(x, y, target_points: int):
        """Échantillonnage uniforme - rapide"""
        if len(x) <= target_points:
            return x, y
            
        step = max(1, len(x) // target_points)
        indices = np.arange(0, len(x), step)
        
        return x[indices], y[indices]


class SeriesRegistry:
    """Source of truth des séries disponibles"""
    
    def __init__(self):
        self._registry = {
            # Séries directes du DataFrame canonique
            "speed": SeriesDefinition(
                name="speed", 
                unit="m/s", 
                x_axes=["time", "distance"], 
                default=True, 
                source_column="speed_m_s"
            ),
            "pace": SeriesDefinition(
                name="pace", 
                unit="s/km", 
                x_axes=["time", "distance"], 
                default=True,
                source_column="pace_s_per_km"
            ), 
            "elevation": SeriesDefinition(
                name="elevation", 
                unit="m", 
                x_axes=["time", "distance"], 
                default=True,
                source_column="elevation"
            ),
            "heart_rate": SeriesDefinition(
                name="heart_rate", 
                unit="bpm", 
                x_axes=["time", "distance"], 
                default=True,
                source_column="heart_rate"
            ),
            "cadence": SeriesDefinition(
                name="cadence", 
                unit="spm", 
                x_axes=["time", "distance"], 
                default=False,
                source_column="cadence"
            ),
            "power": SeriesDefinition(
                name="power", 
                unit="watts", 
                x_axes=["time", "distance"], 
                default=False,
                source_column="power"
            ),
            
            # Séries dérivées (computed)
            "grade": SeriesDefinition(
                name="grade", 
                unit="%", 
                x_axes=["time", "distance"], 
                default=False,
                compute_func=self._compute_grade_series
            ),
            "moving": SeriesDefinition(
                name="moving", 
                unit="bool", 
                x_axes=["time", "distance"], 
                default=False,
                compute_func=self._compute_moving_mask
            ),
            
            # Séries avancées (paramétrées)
            "hr_zones": SeriesDefinition(
                name="hr_zones", 
                unit="zone", 
                x_axes=["time", "distance"], 
                default=False,
                requires_params={"hr_max": int, "hr_min": int}
            ),
            "power_zones": SeriesDefinition(
                name="power_zones", 
                unit="zone", 
                x_axes=["time", "distance"], 
                default=False,
                requires_params={"ftp": int}
            )
        }
        
    def _compute_grade_series(self, df: pd.DataFrame) -> pd.Series:
        """Calcule série de pente (%) via l'implémentation core.

        Important: on applique `fillna(0)` pour garder le comportement historique de
        l'endpoint series (aucun trou dans la serie "grade").
        """
        if "elevation" not in df.columns:
            return pd.Series(0.0, index=df.index)

        working = df
        if "delta_distance_m" not in df.columns:
            if "distance_m" not in df.columns:
                return pd.Series(0.0, index=df.index)
            working = df.assign(delta_distance_m=df["distance_m"].diff())

        grade = compute_grade_percent_series(working, smooth_window=DEFAULT_GRADE_SMOOTH_WINDOW)
        grade = grade.replace([np.inf, -np.inf], np.nan)
        return grade.fillna(0.0)
        
    def _compute_moving_mask(self, df: pd.DataFrame) -> pd.Series:
        """Calcule masque mouvement via l'implémentation core."""
        if "speed_m_s" not in df.columns or "delta_time_s" not in df.columns:
            return pd.Series(False, index=df.index)

        return compute_moving_mask(df)

    @staticmethod
    def _is_numeric_array(arr: np.ndarray) -> bool:
        return bool(np.issubdtype(arr.dtype, np.number))
        
    def get_available_series(self, df: pd.DataFrame) -> List[SeriesInfo]:
        """Retourne séries disponibles selon données présentes"""
        available = []
        
        for name, definition in self._registry.items():
            # Vérifier si série disponible
            if definition.source_column is not None:
                # Série directe - vérifier colonne existe et non vide
                if definition.source_column in df.columns:
                    col_data = df[definition.source_column]
                    if not bool(col_data.isna().all()):
                        available.append(SeriesInfo(
                            name=definition.name,
                            unit=definition.unit,
                            x_axes=definition.x_axes,
                            default=definition.default
                        ))
            else:
                # Série calculée - toujours disponible pour l'instant
                available.append(SeriesInfo(
                    name=definition.name,
                    unit=definition.unit,
                    x_axes=definition.x_axes,
                    default=definition.default
                ))
                
        return available
        
    def _clean_dataframe(self, df: pd.DataFrame):
        """Nettoyage DataFrame pour API"""
        clean_df = df.copy()
        
        # Suppression lignes NaN critiques
        critical_cols = ['time', 'distance_m', 'lat', 'lon']
        critical_cols_existing = [col for col in critical_cols if col in clean_df.columns]
        if len(critical_cols_existing) > 0:
            clean_df = cast(pd.DataFrame, clean_df.dropna(subset=critical_cols_existing))
        
        # Validation cohérence temporelle
        if 'elapsed_time_s' in clean_df.columns:
            clean_df = cast(pd.DataFrame, clean_df.loc[clean_df['elapsed_time_s'] >= 0])
            
        return clean_df
        
    def _slice_dataframe(
        self,
        df: pd.DataFrame,
        x_axis: Literal["time", "distance"],
        from_val: Optional[float],
        to_val: Optional[float],
    ):
        """Slicing selon plage temps/distance"""
        if from_val is None and to_val is None:
            return df
            
        sliced_df = df.copy()
        
        if x_axis == "time":
            x_col = 'elapsed_time_s'
        else:  # distance
            x_col = 'distance_m'
            
        if x_col not in df.columns:
            return cast(pd.DataFrame, df)
            
        # Application filtres
        if from_val is not None:
            sliced_df = cast(pd.DataFrame, sliced_df.loc[sliced_df[x_col] >= from_val])
        if to_val is not None:
            sliced_df = cast(pd.DataFrame, sliced_df.loc[sliced_df[x_col] <= to_val])
            
        return sliced_df
        
    def _downsample_series(self, df: pd.DataFrame, x_axis: Literal["time", "distance"], target_points: int):
        """Application downsampling"""
        # Extraction x/y selon axe
        if x_axis == "time":
            x_data = np.asarray(df['elapsed_time_s'].to_numpy())
        else:  # distance
            x_data = np.asarray(df['distance_m'].to_numpy())
            
        y_data = np.asarray(df.index.to_numpy())  # placeholder
        
        return DownsamplingStrategy.uniform_downsample(x_data, y_data, target_points)
        
    def _extract_raw_series(self, df: pd.DataFrame, x_axis: Literal["time", "distance"], series_name: str):
        """Extraction série brute sans downsampling"""
        # x axis
        if x_axis == "time":
            x_data = np.asarray(df['elapsed_time_s'].to_numpy())
        else:  # distance
            x_data = np.asarray(df['distance_m'].to_numpy())
            
        # y axis - selon définition registry
        definition = self._registry.get(series_name)
        if not definition:
            raise ValueError(f"Series {series_name} not defined")
            
        if definition.source_column is not None:
            y_data = np.asarray(df[definition.source_column].to_numpy())
        elif definition.compute_func:
            y_data = np.asarray(definition.compute_func(df).to_numpy())
        else:
            raise ValueError(f"Series {series_name} has no source_column or compute_func")
            
        return x_data, y_data
        
    def get_series_data(
        self,
        df: pd.DataFrame,
        name: str,
        x_axis: Literal["time", "distance"],
        from_val: Optional[float],
        to_val: Optional[float],
        downsample: Optional[int],
    ) -> SeriesResponse:
        """Extrait/Calcule série avec slicing + downsampling"""
        
        # 1. Validation nom série
        if name not in self._registry:
            raise ValueError(f"Series {name} not available")
            
        definition = self._registry[name]
        
        # 2. Nettoyage DataFrame
        clean_df = self._clean_dataframe(df)
        
        # 3. Slicing selon from/to dans unité x_axis  
        sliced_df = self._slice_dataframe(clean_df, x_axis, from_val, to_val)
        
        x_axis_lit: Literal["time", "distance"] = x_axis

        # 4. Vérifier données disponibles
        if sliced_df.empty:
            return SeriesResponse(
                name=name,
                x_axis=x_axis_lit,
                unit=definition.unit,
                x=[],
                y=[],
                meta=SeriesMeta(
                    downsampled=False,
                    original_points=0,
                    returned_points=0
                )
            )
        
        # 5. Downsampling si demandé
        original_points = len(sliced_df)
        
        if downsample is not None and original_points > downsample:
            x_data, y_data = self._extract_raw_series(sliced_df, x_axis, name)
            x_data, y_data = DownsamplingStrategy.uniform_downsample(x_data, y_data, downsample)
            downsampled = True
            returned_points = len(x_data)
        else:
            x_data, y_data = self._extract_raw_series(sliced_df, x_axis, name)
            downsampled = False
            returned_points = original_points
            
        # 6. Filtrage NaN finaux
        # Notes:
        # - `y_data` peut etre non-numerique (ex: bool pour "moving").
        # - On filtre toujours `x_data` sur finitude.
        valid_mask = np.isfinite(x_data)
        if self._is_numeric_array(y_data):
            valid_mask = valid_mask & np.isfinite(y_data)
        x_data = x_data[valid_mask]
        y_data = y_data[valid_mask]
        
        # 7. Métadonnées
        meta = SeriesMeta(
            downsampled=downsampled,
            original_points=original_points,
            returned_points=returned_points
        )
        
        return SeriesResponse(
            name=name,
            x_axis=x_axis_lit,
            unit=definition.unit,
            x=x_data.tolist(),
            y=y_data.tolist(),
            meta=meta
        )
