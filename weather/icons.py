from __future__ import annotations

import os
import threading
import time
from typing import Optional

from weather.cache_io import (
    _disable_cache_writes,
    _icons_dir,
    _migrate_legacy_weather_storage,
    _read_json,
    _write_json_atomic,
)
from weather.net import _http_get_bytes

__all__ = [
    "get_official_icon_png_path",
    "start_icon_pack_update_async",
]


# ============================================================
# icons (MET Weather API icons) – download/cache por symbol_code
# Fonte: metno/weathericons (PNG nomeado como symbol_code)
# Ex: partlycloudy_day.png, rain.png, cloudy.png...
# ============================================================

def _normalize_symbol_code_candidates(symbol_code: Optional[str], is_day: bool) -> list:
    """
    Gera lista de candidatos de filename-base (sem .png) para tentar resolver ícone.
    Regras:
      - Se já vier com _day/_night/_polartwilight: tenta direto.
      - Se vier sem sufixo: tenta direto e depois tenta adicionar _day/_night.
    """
    if not symbol_code:
        return []

    s = str(symbol_code).strip().lower()
    if not s:
        return []

    if s.endswith("_day") or s.endswith("_night") or s.endswith("_polartwilight"):
        return [s]

    suf = "day" if is_day else "night"
    return [s, f"{s}_{suf}"]


def _icon_url_for_code(code_base: str) -> str:
    # Diretório PNG do metno/weathericons:
    # https://cdn.jsdelivr.net/gh/metno/weathericons@master/weather/png/partlycloudy_day.png
    return f"https://cdn.jsdelivr.net/gh/metno/weathericons@master/weather/png/{code_base}.png"


def get_official_icon_png_path(
    symbol_code: Optional[str],
    is_day: bool,
    app_dir: str,
    logger=None,
    user_agent: str = "CLUBAL-AgendaLive/2.0 (contact: local)",
) -> Optional[str]:
    """
    Resolve e cacheia o PNG oficial por symbol_code.

    Cache:
      <CACHE_ROOT>/weather/weather_icons/<symbol_code>.png

    Estratégia:
      1) tenta achar no cache local
      2) se não existir, baixa do CDN (metno/weathericons) e salva
      3) se falhar, retorna None
    """
    _migrate_legacy_weather_storage(app_dir, logger=logger)

    icons_dir = _icons_dir(app_dir)
    if not icons_dir:
        if logger:
            logger("[WEATHER] Icon cache disabled (no writable cache dir)")
        return None

    candidates = _normalize_symbol_code_candidates(symbol_code, is_day=is_day)
    if not candidates:
        if logger:
            logger("[WEATHER] Icon miss (no symbol_code)")
        return None

    for code_base in candidates:
        local_path = os.path.join(icons_dir, f"{code_base}.png")

        if os.path.exists(local_path):
            return local_path

        url = _icon_url_for_code(code_base)

        try:
            if logger:
                logger(f"[WEATHER] Icon fetch code={code_base} url={url}")

            data = _http_get_bytes(url, user_agent=user_agent, timeout=6, logger=logger)
        except Exception as e:
            if logger:
                logger(f"[WEATHER] Icon download failed code={code_base} err={type(e).__name__}: {e}")
            continue

        tmp = local_path + ".tmp"

        try:
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, local_path)

            if logger:
                logger(f"[WEATHER] Icon cached -> {local_path}")
            return local_path

        except Exception as e:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

            _disable_cache_writes(
                logger=logger,
                reason=f"icon write failed code={code_base} path={local_path}",
            )

            if logger:
                logger(f"[WEATHER] Icon cache write failed code={code_base} err={type(e).__name__}: {e}")
            return None

    return None


# ============================================================
# icon pack prewarm (background) – baixa um conjunto amplo de ícones
# ============================================================

_PREWARM_LOCK = threading.Lock()
_PREWARM_STARTED = False


def _icon_pack_codes_full() -> list[str]:
    """
    Lista ampla (mas segura) de códigos de ícones do metno/weathericons.
    """
    return [
        # céu / nuvens
        "clearsky_day", "clearsky_night",
        "fair_day", "fair_night",
        "partlycloudy_day", "partlycloudy_night",
        "cloudy",
        "fog",

        # chuva / garoa
        "lightrain",
        "rain",
        "heavyrain",
        "lightrainshowers_day", "lightrainshowers_night",
        "rainshowers_day", "rainshowers_night",
        "heavyrainshowers_day", "heavyrainshowers_night",

        # trovoadas
        "rainandthunder",
        "heavyrainandthunder",
        "rainshowersandthunder_day", "rainshowersandthunder_night",
        "heavyrainshowersandthunder_day", "heavyrainshowersandthunder_night",

        # neve
        "lightsnow",
        "snow",
        "heavysnow",
        "lightsnowshowers_day", "lightsnowshowers_night",
        "snowshowers_day", "snowshowers_night",
        "heavysnowshowers_day", "heavysnowshowers_night",

        # neve com trovoada
        "snowandthunder",
        "snowshowersandthunder_day", "snowshowersandthunder_night",

        # sleet (chuva congelada)
        "lightsleet",
        "sleet",
        "heavysleet",
        "lightsleetshowers_day", "lightsleetshowers_night",
        "sleetshowers_day", "sleetshowers_night",
        "heavysleetshowers_day", "heavysleetshowers_night",

        # sleet com trovoada
        "sleetandthunder",
        "sleetshowersandthunder_day", "sleetshowersandthunder_night",

        # extras comuns do pack (dependendo da versão do metno/weathericons)
        "partlycloudy_polartwilight",
        "clearsky_polartwilight",
        "fair_polartwilight",
    ]


def start_icon_pack_update_async(
    app_dir: str,
    logger=None,
    user_agent: str = "CLUBAL-AgendaLive/2.0 (contact: local)",
    max_download: int = 9999,
) -> None:
    """
    Pre-warm (background): tenta baixar um conjunto amplo de ícones comuns.
    - Não bloqueia o app.
    - Só baixa o que não existir no cache.
    - Não repete sem necessidade (1x por dia, por usuário/máquina).
    - Protege contra chamada duplicada.
    """
    global _PREWARM_STARTED

    with _PREWARM_LOCK:
        if _PREWARM_STARTED:
            return
        _PREWARM_STARTED = True

    def _worker():
        try:
            icons_dir = _icons_dir(app_dir)
            if not icons_dir:
                if logger:
                    logger("[WEATHER] Prewarm skip (icon cache disabled: no writable cache dir)")
                return

            stamp_path = os.path.join(icons_dir, "_prewarm_stamp.json")
            today_key = time.strftime("%Y-%m-%d")

            try:
                stamp = _read_json(stamp_path) or {}
                if stamp.get("day") == today_key:
                    if logger:
                        logger(f"[WEATHER] Prewarm skip (already ran today) day={today_key}")
                    return
            except Exception:
                pass

            codes = _icon_pack_codes_full()

            downloaded = 0
            for code in codes:
                if downloaded >= int(max_download):
                    break

                p = os.path.join(icons_dir, f"{code}.png")
                if os.path.exists(p):
                    continue

                url = _icon_url_for_code(code)
                try:
                    data = _http_get_bytes(url, user_agent=user_agent, timeout=6, logger=logger)
                except Exception:
                    continue

                tmp = p + ".tmp"
                try:
                    with open(tmp, "wb") as f:
                        f.write(data)
                    os.replace(tmp, p)
                    downloaded += 1
                    if logger:
                        logger(f"[WEATHER] Prewarm cached -> {p}")
                except Exception as e:
                    try:
                        if os.path.exists(tmp):
                            os.remove(tmp)
                    except Exception:
                        pass

                    _disable_cache_writes(
                        logger=logger,
                        reason=f"prewarm write failed code={code} path={p}",
                    )

                    if logger:
                        logger(f"[WEATHER] Prewarm cache write failed code={code} err={type(e).__name__}: {e}")
                    return

            try:
                _write_json_atomic(
                    stamp_path,
                    {"day": today_key, "downloaded": int(downloaded), "ts": int(time.time())},
                )
            except Exception:
                pass

            if logger:
                logger(f"[WEATHER] Prewarm done downloaded={downloaded} day={today_key}")

        except Exception as e:
            if logger:
                logger(f"[WEATHER] Prewarm error {type(e).__name__}: {e}")

    t = threading.Thread(target=_worker, name="weather_icon_prewarm", daemon=True)
    t.start()