from __future__ import annotations


__all__ = [
    "WEATHER_PLACE_CITY",
    "WEATHER_PLACE_UF",
    "WEATHER_LAT",
    "WEATHER_LON",
    "get_place_display",
]

WEATHER_PLACE_CITY = "Alfenas"   # <<< cidade (ex: "Varginha")
WEATHER_PLACE_UF = "MG"          # <<< UF (ex: "SP", "RJ", "RS")
WEATHER_LAT = -21.4267           # <<< latitude
WEATHER_LON = -45.9470           # <<< longitude


def get_place_display() -> str:
    """
    Exibição padronizada para topo do WeatherCard.
    Ex: "ALFENAS - MG"
    """
    city = (WEATHER_PLACE_CITY or "").strip().upper()
    uf = (WEATHER_PLACE_UF or "").strip().upper()
    if city and uf:
        return f"{city} - {uf}"
    return city or uf or "LOCAL"