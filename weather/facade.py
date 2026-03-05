"""
CLUBAL – Weather service (online + cache)

Fachada pública do backend de clima.
A implementação foi modularizada em `weather/*`.

Este módulo é a "API oficial" dentro do pacote `weather`.
"""

from __future__ import annotations

from weather.models import WeatherResult
from weather.config import (
    WEATHER_LAT,
    WEATHER_LON,
    WEATHER_PLACE_CITY,
    WEATHER_PLACE_UF,
    get_place_display,
)
from weather.icons import (
    get_official_icon_png_path,
    start_icon_pack_update_async,
)
from weather.cache_io import housekeeping
from weather.service import get_weather

__all__ = [
    "start_icon_pack_update_async",
    "WeatherResult",
    "get_weather",
    "get_official_icon_png_path",
    "housekeeping",
    "get_place_display",
    "WEATHER_PLACE_CITY",
    "WEATHER_PLACE_UF",
    "WEATHER_LAT",
    "WEATHER_LON",
]