"""Weather integration boundary for race planning.

CourseScope intentionally ships without an external weather dependency. A
provider can be injected later without changing the deterministic planning
pipeline or making preview requests fail when weather is unavailable.
"""

from __future__ import annotations

from typing import Protocol


class WeatherProvider(Protocol):
    def get_forecast(self, *, latitude: float, longitude: float, at_iso: str) -> dict[str, object] | None: ...


class NullWeatherProvider:
    def get_forecast(self, *, latitude: float, longitude: float, at_iso: str) -> None:
        return None
