"""
CLUBAL – Header Weather UI

Compat shim.

Mantém import compatibility:
  from ui.header_weather import WeatherCard

A implementação real agora vive em:
  ui.weather_card
"""

from __future__ import annotations

from ui.weather_card import WeatherCard

__all__ = ["WeatherCard"]