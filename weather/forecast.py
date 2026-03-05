from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from weather.cache_io import _safe_int
from weather.config import (
    WEATHER_PLACE_CITY,
    WEATHER_PLACE_UF,
    get_place_display,
)
from weather.models import WeatherResult


__all__ = ["_extract_summary"]


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
    day_add: int = 0,
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