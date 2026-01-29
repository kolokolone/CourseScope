"""Constantes partagees (sans Streamlit).

Ce module centralise les seuils et valeurs par defaut utilises dans core/ et services/.
Garder ce module sans dependances (hors stdlib).
"""

from __future__ import annotations


# Bornes de vitesse canoniques utilisees pour deriver allure/vitesse depuis les points GPS.
# Ces valeurs sont volontairement conservatrices pour filtrer les pics irrealisables.
MIN_SPEED_M_S: float = 0.5  # ~33 min/km
MAX_SPEED_M_S: float = 8.0  # ~2:05 min/km

# Distance minimale requise pour faire confiance a une vitesse instantanee.
MIN_DISTANCE_FOR_SPEED_M: float = 0.5

# Seuil "en mouvement" (m/s). On utilise la meme base que MIN_SPEED_M_S.
MOVING_SPEED_THRESHOLD_M_S: float = MIN_SPEED_M_S

# Fenetres de lissage par defaut.
DEFAULT_GRADE_SMOOTH_WINDOW: int = 5

# Detection de pause.
DEFAULT_MIN_PAUSE_DURATION_S: float = 5.0
