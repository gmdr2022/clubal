"""
CLUBAL – Weather service (online + cache)

Este módulo é o backend de clima do CLUBAL:
- Consumir met.no Locationforecast (compact) e extrair:
  - temperatura atual
  - label de “agora” (hoje) e uma frase de forecast intuitiva
  - symbol_code para ícone (compatível com símbolos do Yr)
- Persistir cache local (para modo offline).
- Baixar e cachear ícones oficiais do Yr (PNG) por symbol_code.
- Housekeeping: rotação de caches antigos + limpeza leve de ícones.

Notas:
- Cache/ícones ficam no diretório gravável por usuário (LOCALAPPDATA), definido em _cache_root().
- Este módulo não depende do nome do arquivo principal (clubal.py); o vínculo é apenas via import e chamadas.

Estrutura (candidata a desmembramento futuro):
- config: WEATHER_PLACE_*
- cache_io: _cache_root/_cache_paths/_read_json/_write_json_atomic/housekeeping
- net: _ssl_context_best_effort/_build_opener/_http_get_json/_http_get_bytes
- icons: mapping + get_official_icon_png_path
- forecast: regras de composição de labels + _extract_summary
- public api: get_weather()
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Tuple
from weather.models import WeatherResult
from weather.config import (
    WEATHER_LAT,
    WEATHER_LON,
    WEATHER_PLACE_CITY,
    WEATHER_PLACE_UF,
    get_place_display,
)
from weather.net import (
    _http_get_bytes,
    _http_get_json,
)
from weather.icons import (
    get_official_icon_png_path,
    start_icon_pack_update_async,
)
from weather.cache_io import (
    CACHE_ARCHIVE_DIRNAME,
    CACHE_ARCHIVE_KEEP,
    CACHE_ARCHIVE_MAX_AGE_DAYS,
    ICONS_DIRNAME,
    ICON_STALE_DAYS,
    _archive_existing_cache,
    _cache_paths,
    _cache_root,
    _cleanup_cache_archive,
    _icons_dir,
    _read_json,
    _safe_int,
    _safe_mkdir,
    _write_json_atomic,
    _migrate_legacy_weather_storage,
    housekeeping,
)
from weather.forecast import _extract_summary

__all__ = [
    "start_icon_pack_update_async",
    "WeatherResult",
    "get_weather",
    "get_official_icon_png_path",
    "housekeeping",
    "get_place_display",
]

# ============================================================
# Public API
# ============================================================

def get_weather(
    city_label: str,
    lat: float,
    lon: float,
    app_dir: str,
    user_agent: str = "CLUBAL-AgendaLive/2.0 (contact: local)",
    logger=None,
) -> WeatherResult:
    current_cache_path, archive_dir = _cache_paths(app_dir)
    _migrate_legacy_weather_storage(app_dir, logger=logger)
    now_hour = time.localtime().tm_hour

    use_lat = float(lat) if lat is not None else float(WEATHER_LAT)
    use_lon = float(lon) if lon is not None else float(WEATHER_LON)

    url = (
        "https://api.met.no/weatherapi/locationforecast/2.0/compact"
        f"?lat={use_lat:.4f}&lon={use_lon:.4f}"
    )

    cache_enabled = bool(current_cache_path and archive_dir)

    try:
        if logger:
            logger(f"[WEATHER] Fetch start url={url} cache={'on' if cache_enabled else 'off'}")

        payload = _http_get_json(url, user_agent=user_agent, timeout=6, logger=logger)
        res = _extract_summary(payload, now_hour=now_hour, lat=use_lat, lon=use_lon)

        if cache_enabled:
            cache_path = current_cache_path
            cache_archive_dir = archive_dir

            if cache_path is not None and cache_archive_dir is not None:
                _archive_existing_cache(cache_path, cache_archive_dir, logger=logger)
                _write_json_atomic(
                    cache_path,
                    {
                        "ts": res.cache_ts,
                        "payload": payload,
                        "city": (WEATHER_PLACE_CITY or city_label),
                        "uf": (WEATHER_PLACE_UF or ""),
                        "lat": use_lat,
                        "lon": use_lon,
                    },
                )
                _cleanup_cache_archive(cache_archive_dir, logger=logger)

                if logger:
                    logger(f"[WEATHER] ONLINE ok temp={res.temp_c} sym={res.symbol_code} cache_path={cache_path}")
            else:
                if logger:
                    logger(f"[WEATHER] ONLINE ok temp={res.temp_c} sym={res.symbol_code} (cache disabled)")
        else:
            if logger:
                logger(f"[WEATHER] ONLINE ok temp={res.temp_c} sym={res.symbol_code} (cache disabled)")

        return res

    except Exception:
        if cache_enabled:
            cache_path = current_cache_path

            if cache_path is not None:
                cached = _read_json(cache_path)
                if cached and isinstance(cached.get("payload"), dict):
                    payload = cached["payload"]

                    c_lat = cached.get("lat", use_lat)
                    c_lon = cached.get("lon", use_lon)

                    res = _extract_summary(payload, now_hour=now_hour, lat=float(c_lat), lon=float(c_lon))
                    res.source = "cache"
                    res.cache_ts = cached.get("ts")
                    res.ok = True

                    if logger:
                        logger(f"[WEATHER] FALLBACK cache ok ts={res.cache_ts} cache_path={cache_path}")

                    return res

        if logger:
            logger("[WEATHER] FAIL no cache available (or cache disabled)")

        return WeatherResult(
            ok=False,
            temp_c=None,
            today_label="Sem dados",
            tomorrow_label="Amanhã: —",
            symbol_code=None,
            source="cache",
            cache_ts=None,
            place_city=(WEATHER_PLACE_CITY or "Local"),
            place_uf=(WEATHER_PLACE_UF or "--"),
            place_display=get_place_display(),
            lat=float(use_lat),
            lon=float(use_lon),
        )
