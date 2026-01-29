from dataclasses import dataclass
from typing import List, Literal, Optional, Callable, Dict, Any
import pandas as pd
import numpy as np

from api.schemas import SeriesInfo, SeriesResponse, SeriesMeta


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
    def lttb_downsample(x: np.ndarray, y: np.ndarray, target_points: int) -> tuple:
        """Largest-Triangle-Three-Buckets - préserve features"""
        if len(x) <= target_points:
            return x, y
            
        # Simplification : échantillonnage uniforme pour MVP
        # TODO: implémenter vrai LTTB plus tard
        step = max(1, len(x) // target_points)
        indices = np.arange(0, len(x), step)
        
        return x[indices], y[indices]
        
    @staticmethod  
    def uniform_downsample(x: np.ndarray, y: np.ndarray, target_points: int) -> tuple:
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
        """Calcule série de pente (%)"""
        if 'elevation' not in df.columns or 'distance_m' not in df.columns:
            return pd.Series(np.nan, index=df.index)
            
        # Pente = (elevation_diff) / (distance_diff) * 100
        elevation_diff = df['elevation'].diff()
        distance_diff = df['distance_m'].diff()
        
        # Éviter division par zéro
        with np.errstate(divide='ignore', invalid='ignore'):
            grade = (elevation_diff / distance_diff) * 100
            
        return grade.fillna(0)
        
    def _compute_moving_mask(self, df: pd.DataFrame) -> pd.Series:
        """Calcule masque mouvement (vitesse > 0.5 m/s)"""
        if 'speed_m_s' not in df.columns:
            return pd.Series(False, index=df.index)
            
        return df['speed_m_s'] > 0.5
        
    def get_available_series(self, df: pd.DataFrame) -> List[SeriesInfo]:
        """Retourne séries disponibles selon données présentes"""
        available = []
        
        for name, definition in self._registry.items():
            # Vérifier si série disponible
            if definition.source_column:
                # Série directe - vérifier colonne existe et non vide
                if definition.source_column in df.columns:
                    col_data = df[definition.source_column]
                    if not col_data.isna().all():
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
        
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nettoyage DataFrame pour API"""
        clean_df = df.copy()
        
        # Suppression lignes NaN critiques
        critical_cols = ['time', 'distance_m', 'lat', 'lon']
        critical_cols_existing = [col for col in critical_cols if col in clean_df.columns]
        if critical_cols_existing:
            clean_df = clean_df.dropna(subset=critical_cols_existing)
        
        # Validation cohérence temporelle
        if 'elapsed_time_s' in clean_df.columns:
            clean_df = clean_df[clean_df['elapsed_time_s'] >= 0]
            
        return clean_df
        
    def _slice_dataframe(self, df: pd.DataFrame, x_axis: str, 
                        from_val: Optional[float], to_val: Optional[float]) -> pd.DataFrame:
        """Slicing selon plage temps/distance"""
        if from_val is None and to_val is None:
            return df
            
        sliced_df = df.copy()
        
        if x_axis == "time":
            x_col = 'elapsed_time_s'
        else:  # distance
            x_col = 'distance_m'
            
        if x_col not in df.columns:
            return df
            
        # Application filtres
        if from_val is not None:
            sliced_df = sliced_df[sliced_df[x_col] >= from_val]
        if to_val is not None:
            sliced_df = sliced_df[sliced_df[x_col] <= to_val]
            
        return sliced_df
        
    def _downsample_series(self, df: pd.DataFrame, x_axis: str, 
                          target_points: int) -> tuple[np.ndarray, np.ndarray]:
        """Application downsampling"""
        # Extraction x/y selon axe
        if x_axis == "time":
            x_data = df['elapsed_time_s'].values
        else:  # distance
            x_data = df['distance_m'].values
            
        y_data = df.index.values  # placeholder
        
        return DownsamplingStrategy.uniform_downsample(x_data, y_data, target_points)
        
    def _extract_raw_series(self, df: pd.DataFrame, x_axis: str, series_name: str) -> tuple[np.ndarray, np.ndarray]:
        """Extraction série brute sans downsampling"""
        # x axis
        if x_axis == "time":
            x_data = df['elapsed_time_s'].values
        else:  # distance
            x_data = df['distance_m'].values
            
        # y axis - selon définition registry
        definition = self._registry.get(series_name)
        if not definition:
            raise ValueError(f"Series {series_name} not defined")
            
        if definition.source_column:
            y_data = df[definition.source_column].values
        elif definition.compute_func:
            y_data = definition.compute_func(df).values
        else:
            raise ValueError(f"Series {series_name} has no source_column or compute_func")
            
        return x_data, y_data
        
    def get_series_data(self, df: pd.DataFrame, name: str, x_axis: str, 
                       from_val: Optional[float], to_val: Optional[float],
                       downsample: Optional[int], params: dict = None) -> SeriesResponse:
        """Extrait/Calcule série avec slicing + downsampling"""
        
        # 1. Validation nom série
        if name not in self._registry:
            raise ValueError(f"Series {name} not available")
            
        definition = self._registry[name]
        
        # 2. Nettoyage DataFrame
        clean_df = self._clean_dataframe(df)
        
        # 3. Slicing selon from/to dans unité x_axis  
        sliced_df = self._slice_dataframe(clean_df, x_axis, from_val, to_val)
        
        # 4. Vérifier données disponibles
        if sliced_df.empty:
            return SeriesResponse(
                name=name,
                x_axis=x_axis,
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
        
        if downsample and original_points > downsample:
            x_data, y_data = self._extract_raw_series(sliced_df, x_axis, name)
            x_data, y_data = DownsamplingStrategy.uniform_downsample(x_data, y_data, downsample)
            downsampled = True
            returned_points = len(x_data)
        else:
            x_data, y_data = self._extract_raw_series(sliced_df, x_axis, name)
            downsampled = False
            returned_points = original_points
            
        # 6. Filtrage NaN finaux
        valid_mask = ~(np.isnan(x_data) | np.isnan(y_data))
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
            x_axis=x_axis,
            unit=definition.unit,
            x=x_data.tolist(),
            y=y_data.tolist(),
            meta=meta
        )