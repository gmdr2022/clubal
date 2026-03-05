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

__all__ = [
    "start_icon_pack_update_async",
    "WeatherResult",
    "get_weather",
    "get_official_icon_png_path",
    "housekeeping",
    "get_place_display",
]
# ============================================================
# forecast (extração e composição de labels)
# ============================================================

def _local_utc_offset_seconds() -> int:
    try:
        if time.daylight and time.localtime().tm_isdst:
            return -time.altzone
        return -time.timezone
    except Exception:
        return 0


def _parse_iso_utc_to_local(iso_s: str):
    try:
        from datetime import datetime
        s = str(iso_s or "").strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt_utc = datetime.fromisoformat(s)
        ts = dt_utc.timestamp()
        off = _local_utc_offset_seconds()
        return datetime.fromtimestamp(ts + off)
    except Exception:
        return None


def _symbol_score(sym: Optional[str]) -> Tuple[int, str]:
    if not sym:
        return (0, "Sem dados")
    s = sym.lower()

    if "thunder" in s:
        return (4, "Tempestade")
    if "snow" in s:
        return (3, "Neve")
    if "rain" in s or "sleet" in s:
        if "heavy" in s:
            return (3, "Chuva forte")
        if "light" in s:
            return (2, "Chuva fraca")
        return (2, "Chuva")
    if "cloudy" in s:
        return (1, "Parcialmente nublado" if "partly" in s else "Nublado")
    if "clearsky" in s or "fair" in s:
        return (0, "Céu limpo")
    return (1, "Tempo instável")


def _precip_max_from_item(item: Dict[str, Any]) -> float:
    """
    Pega um "sinal" de precipitação do timeseries:
    - next_1_hours.details.precipitation_amount (ou max/min)
    - next_6_hours.details.precipitation_amount (fallback)
    """
    try:
        data = item.get("data", {}) or {}
        for key in ("next_1_hours", "next_6_hours"):
            block = data.get(key, {}) or {}
            det = block.get("details", {}) or {}
            v = det.get("precipitation_amount")
            if v is None:
                v = det.get("precipitation_amount_max")
            if v is None:
                v = det.get("precipitation_amount_min")
            if v is not None:
                return float(v)
    except Exception:
        pass
    return 0.0


def _cloud_fraction_from_item(item: Dict[str, Any]) -> Optional[float]:
    """
    Tenta extrair nebulosidade (%) do bloco instant.details.cloud_area_fraction.
    Retorna None se não existir.
    """
    try:
        data = item.get("data", {}) or {}
        instant = (data.get("instant", {}) or {}).get("details", {}) or {}
        v = instant.get("cloud_area_fraction")
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _choose_live_symbol_code(first_item: Dict[str, Any], now_hour: int) -> Optional[str]:
    """
    Decide o symbol_code para o ÍCONE do 'AGORA' com comportamento mais 'ao vivo':
    - Se houver precipitação relevante na próxima 1h, mantém o símbolo de chuva/trovoada/etc.
    - Se precipitação for ~0, troca para um símbolo baseado na nebulosidade (cloud_area_fraction).
    - Importante: quando o símbolo precisar de variação dia/noite, retorna com sufixo _day/_night.
    """
    try:
        data = first_item.get("data", {}) or {}

        n1 = ((data.get("next_1_hours", {}) or {}).get("summary", {}) or {}).get("symbol_code")
        n6 = ((data.get("next_6_hours", {}) or {}).get("summary", {}) or {}).get("symbol_code")
        sym_forecast = n1 or n6

        precip = 0.0
        try:
            det1 = ((data.get("next_1_hours", {}) or {}).get("details", {}) or {})
            v = det1.get("precipitation_amount")
            if v is None:
                v = det1.get("precipitation_amount_max")
            if v is None:
                v = det1.get("precipitation_amount_min")
            if v is not None:
                precip = float(v)
        except Exception:
            precip = 0.0

        PRECIP_LIVE_THRESHOLD = 0.2

        # Se já tem símbolo de forecast e a chuva é relevante, confia nele (normalmente já vem com _day/_night quando aplicável)
        if sym_forecast and precip >= PRECIP_LIVE_THRESHOLD:
            return sym_forecast

        # Sem chuva relevante: usa nebulosidade para "ao vivo"
        cf = _cloud_fraction_from_item(first_item)
        if cf is None:
            return sym_forecast

        is_day = (6 <= int(now_hour) <= 17)

        if cf >= 80.0:
            return "cloudy"

        if cf >= 45.0:
            return "partlycloudy_day" if is_day else "partlycloudy_night"

        # Poucas nuvens
        return "fair_day" if is_day else "clearsky_night"

    except Exception:
        return None

def _max_symbol_in_window(
    timeseries: list,
    start_h: int,
    end_h: int,
    day_add: int = 0
) -> Tuple[int, str, float]:
    from datetime import datetime, timedelta

    now_local = datetime.now()
    base = (now_local.date() + timedelta(days=day_add))
    best_score = -1
    best_label = "Sem dados"
    best_precip = 0.0

    for item in timeseries:
        t_iso = item.get("time")
        dt_local = _parse_iso_utc_to_local(t_iso)
        if not dt_local:
            continue

        if dt_local.date() != base:
            continue

        if not (start_h <= dt_local.hour <= end_h):
            continue

        data = item.get("data", {}) or {}
        sym = (
            ((data.get("next_1_hours", {}) or {}).get("summary", {}) or {}).get("symbol_code")
            or
            ((data.get("next_6_hours", {}) or {}).get("summary", {}) or {}).get("symbol_code")
        )

        score, label = _symbol_score(sym)
        precip = _precip_max_from_item(item)

        if score > best_score:
            best_score = score
            best_label = label
            best_precip = precip
        elif score == best_score:
            if precip > best_precip:
                best_precip = precip

    if best_score < 0:
        return (0, "Sem dados", 0.0)
    return (best_score, best_label, float(best_precip))


def _needs_possibility_prefix(label: str, precip_hint: float) -> bool:
    """
    Heurística simples:
    - Se for chuva fraca/chuva, mas precipitação esperada muito baixa, usamos "Possibilidade de".
    """
    l = (label or "").lower()
    if "chuva" in l and precip_hint <= 0.3:
        return True
    if "tempestade" in l and precip_hint <= 0.3:
        return True
    return False


def _build_intuitive_forecast(timeseries: list, now_hour: int) -> str:
    if 6 <= now_hour <= 11:
        sc, label, pmax = _max_symbol_in_window(timeseries, start_h=12, end_h=17, day_add=0)
        if label == "Sem dados":
            return "Hoje à tarde: —"
        pref = "Possibilidade de " if _needs_possibility_prefix(label, pmax) else ""
        if sc >= 2:
            return f"{pref}{label} hoje à tarde!"
        return f"{label} hoje à tarde."

    if 12 <= now_hour <= 17:
        sc, label, pmax = _max_symbol_in_window(timeseries, start_h=18, end_h=23, day_add=0)
        if label == "Sem dados":
            return "Hoje à noite: —"
        pref = "Possibilidade de " if _needs_possibility_prefix(label, pmax) else ""
        if sc >= 2:
            return f"{pref}{label} hoje à noite!"
        return f"{label} hoje à noite."

    segs = [
        ("manhã", 6, 11),
        ("tarde", 12, 17),
        ("noite", 18, 23),
    ]

    per = []
    for name, a, b in segs:
        sc, lab, pmax = _max_symbol_in_window(timeseries, start_h=a, end_h=b, day_add=1)
        per.append((name, sc, lab, pmax))

    if all(lab == "Sem dados" for (_n, _sc, lab, _p) in per):
        return "Amanhã: —"

    if all(sc == 0 and lab != "Sem dados" for (_n, sc, lab, _p) in per):
        return "Amanhã: Sol o dia todo!"

    best = max(per, key=lambda t: (t[1], t[3]))
    name, sc, lab, pmax = best
    if lab == "Sem dados":
        return "Amanhã: —"

    pref = "Possibilidade de " if _needs_possibility_prefix(lab, pmax) else ""
    if sc >= 2:
        return f"Amanhã: {pref}{lab} à {name}!"
    return f"Amanhã: {lab} à {name}."


def _pick_period(now_hour: int) -> str:
    if 6 <= now_hour <= 11:
        return "manhã"
    if 12 <= now_hour <= 17:
        return "tarde"
    return "noite"


def _extract_summary(payload: Dict[str, Any], now_hour: int, lat: float, lon: float) -> WeatherResult:
    props = payload.get("properties", {}) or {}
    timeseries = props.get("timeseries", []) or []

    temp_now: Optional[int] = None
    symbol_code: Optional[str] = None

    if timeseries:
        first = timeseries[0].get("data", {}) or {}
        temp_now = _safe_int(((first.get("instant", {}) or {}).get("details", {}) or {}).get("air_temperature"))

        try:
            symbol_code = _choose_live_symbol_code(timeseries[0], now_hour=now_hour)
        except Exception:
            symbol_code = None

    period = _pick_period(now_hour)
    _sc_now, now_label = _symbol_score(symbol_code)
    today_label = f"Agora ({period}): {now_label}"

    forecast_text = _build_intuitive_forecast(timeseries, now_hour=now_hour)

    city = (WEATHER_PLACE_CITY or "").strip()
    uf = (WEATHER_PLACE_UF or "").strip()
    display = get_place_display()

    return WeatherResult(
        ok=True,
        temp_c=temp_now,
        today_label=today_label,
        tomorrow_label=forecast_text,
        symbol_code=symbol_code,
        source="online",
        cache_ts=int(time.time()),
        place_city=city or "Local",
        place_uf=uf or "--",
        place_display=display,
        lat=float(lat),
        lon=float(lon),
    )


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
