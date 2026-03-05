from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


__all__ = ["WeatherResult"]


@dataclass
class WeatherResult:
    ok: bool
    temp_c: Optional[int]

    # Textos prontos para o WeatherCard
    today_label: str
    tomorrow_label: str

    # Ícone do “agora” (met.no symbol_code ou fallback)
    symbol_code: Optional[str]

    # Origem do dado (online/cache) e timestamp do cache (quando existir)
    source: str                # "online" | "cache"
    cache_ts: Optional[int]

    # Local associado ao resultado (para UI e rastreio)
    place_city: str
    place_uf: str
    place_display: str
    lat: float
    lon: float