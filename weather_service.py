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
import ssl
import time
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import urllib.request
import urllib.error

from core.environment import detect_environment
from core.paths import build_paths, cache_subdir


_ENV = detect_environment()
_PATHS = build_paths(_ENV)


__all__ = [
    "start_icon_pack_update_async",
    "WeatherResult",
    "get_weather",
    "get_official_icon_png_path",
    "housekeeping",
    "get_place_display",
]

def _migrate_legacy_weather_storage(app_dir: str, logger=None) -> None:
    """
    Migra layout antigo (se existir) para o padrão definitivo:

    Antigos (legado):
      <CACHE_ROOT>/weather_cache.json
      <CACHE_ROOT>/weather_icons/
      <CACHE_ROOT>/cache_old/
      <CACHE_ROOT>/weather/weather_cache.json  (se já existir, não mexe)

    Novo (padrão):
      <CACHE_ROOT>/weather/weather_cache.json
      <CACHE_ROOT>/weather/weather_icons/
      <CACHE_ROOT>/weather/cache_old/
    """
    try:
        # Se não temos cache gravável, não migra nada
        if _PATHS.cache_dir is None:
            return

        cache_root = str(_PATHS.cache_dir)  # <CACHE_ROOT>
        new_root = _cache_root(app_dir)     # <CACHE_ROOT>/weather
        if not new_root:
            return

        new_cache = os.path.join(new_root, "weather_cache.json")
        new_icons = os.path.join(new_root, ICONS_DIRNAME)  # weather_icons
        new_archive = os.path.join(new_root, CACHE_ARCHIVE_DIRNAME)  # cache_old

        _safe_mkdir(new_icons)
        _safe_mkdir(new_archive)

        # 1) mover weather_cache.json solto para dentro de /weather/
        old_cache = os.path.join(cache_root, "weather_cache.json")
        if (not os.path.exists(new_cache)) and os.path.exists(old_cache):
            try:
                os.replace(old_cache, new_cache)
                if logger:
                    logger(f"[WEATHER] Migrated legacy cache -> {new_cache}")
            except Exception as e:
                if logger:
                    logger(f"[WEATHER] Legacy cache migrate failed {type(e).__name__}: {e}")

        # 2) mover weather_icons/ solto para dentro de /weather/weather_icons/
        old_icons = os.path.join(cache_root, ICONS_DIRNAME)
        if os.path.isdir(old_icons):
            try:
                for name in os.listdir(old_icons):
                    src = os.path.join(old_icons, name)
                    dst = os.path.join(new_icons, name)
                    if not os.path.isfile(src):
                        continue
                    if os.path.exists(dst):
                        continue
                    try:
                        os.replace(src, dst)
                    except Exception:
                        pass
                # tenta remover pasta antiga se ficou vazia
                try:
                    if not os.listdir(old_icons):
                        os.rmdir(old_icons)
                except Exception:
                    pass
                if logger:
                    logger(f"[WEATHER] Migrated legacy icons -> {new_icons}")
            except Exception as e:
                if logger:
                    logger(f"[WEATHER] Legacy icons migrate failed {type(e).__name__}: {e}")

        # 3) mover cache_old/ solto para dentro de /weather/cache_old/
        old_archive = os.path.join(cache_root, CACHE_ARCHIVE_DIRNAME)
        if os.path.isdir(old_archive):
            try:
                for name in os.listdir(old_archive):
                    src = os.path.join(old_archive, name)
                    dst = os.path.join(new_archive, name)
                    if not os.path.isfile(src):
                        continue
                    if os.path.exists(dst):
                        continue
                    try:
                        os.replace(src, dst)
                    except Exception:
                        pass
                # tenta remover pasta antiga se ficou vazia
                try:
                    if not os.listdir(old_archive):
                        os.rmdir(old_archive)
                except Exception:
                    pass
                if logger:
                    logger(f"[WEATHER] Migrated legacy archive -> {new_archive}")
            except Exception as e:
                if logger:
                    logger(f"[WEATHER] Legacy archive migrate failed {type(e).__name__}: {e}")

    except Exception:
        pass

# ============================================================
# config (fonte única de verdade local – pode virar arquivo depois)
# ============================================================

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


# ============================================================
# data model
# ============================================================

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


# ============================================================
# cache policy / housekeeping
# ============================================================

CACHE_ARCHIVE_DIRNAME = "cache_old"
CACHE_ARCHIVE_KEEP = 10                 # mantém últimos N caches antigos
CACHE_ARCHIVE_MAX_AGE_DAYS = 7          # apaga cache_old com mais de N dias

ICONS_DIRNAME = "weather_icons"         # cache dos PNGs oficiais
ICON_STALE_DAYS = 60                    # (opcional) rebaixar se quiser (não obrigatório)


# ============================================================
# cache_io helpers (candidato a módulo cache_io.py)
# ============================================================

def _safe_int(x: Any) -> Optional[int]:
    try:
        return int(round(float(x)))
    except Exception:
        return None


def _safe_mkdir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_json_atomic(path: str, data: Dict[str, Any]) -> None:
    d = os.path.dirname(path)
    _safe_mkdir(d)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _cache_root(app_dir: str) -> Optional[str]:
    """
    Raiz gravável para cache do weather_service.

    Padrão definitivo:
      <CACHE_ROOT>/weather/

    Onde <CACHE_ROOT> vem do core/paths (installed/portable) ou None se não gravável.
    """
    _ = app_dir  # compat

    # Tudo do weather vive dentro do subdir "weather"
    p = cache_subdir(_PATHS, "weather")
    if p is None:
        return None
    return str(p)


def _cache_paths(app_dir: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Retorna:
      - current cache JSON: <CACHE_ROOT>/weather/weather_cache.json
      - archive dir:        <CACHE_ROOT>/weather/cache_old/
    """
    root = _cache_root(app_dir)
    if not root:
        return None, None

    current = os.path.join(root, "weather_cache.json")
    archive = os.path.join(root, CACHE_ARCHIVE_DIRNAME)  # "cache_old"
    _safe_mkdir(archive)
    return current, archive


def _icons_dir(app_dir: str) -> Optional[str]:
    """
    Ícones oficiais (PNG) cacheados em:
      <CACHE_ROOT>/weather/weather_icons/
    """
    root = _cache_root(app_dir)
    if not root:
        return None

    p = os.path.join(root, ICONS_DIRNAME)  # "weather_icons"
    _safe_mkdir(p)
    return p

def _archive_existing_cache(current_path: str, archive_dir: str, logger=None) -> None:
    try:
        if not os.path.exists(current_path):
            return

        cached = _read_json(current_path) or {}
        ts = cached.get("ts")
        if isinstance(ts, int) and ts > 0:
            stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(ts))
        else:
            stamp = time.strftime("%Y%m%d_%H%M%S")

        dst = os.path.join(archive_dir, f"weather_cache_{stamp}.json")
        if os.path.exists(dst):
            dst = os.path.join(archive_dir, f"weather_cache_{stamp}_{int(time.time())}.json")

        os.replace(current_path, dst)
        if logger:
            logger(f"[WEATHER] Archived old cache -> {dst}")

    except Exception as e:
        if logger:
            logger(f"[WEATHER] Archive cache error {type(e).__name__}: {e}")


def _cleanup_cache_archive(archive_dir: str, logger=None) -> None:
    try:
        now = time.time()
        max_age = CACHE_ARCHIVE_MAX_AGE_DAYS * 86400

        files = []
        for name in os.listdir(archive_dir):
            p = os.path.join(archive_dir, name)
            if not os.path.isfile(p):
                continue
            try:
                st = os.stat(p)
            except Exception:
                continue

            if max_age > 0 and (now - st.st_mtime) > max_age:
                try:
                    os.remove(p)
                    if logger:
                        logger(f"[WEATHER] Pruned old archive (age) {p}")
                except Exception:
                    pass
                continue

            files.append((st.st_mtime, p))

        files.sort(reverse=True)  # newest first
        for _mtime, p in files[CACHE_ARCHIVE_KEEP:]:
            try:
                os.remove(p)
                if logger:
                    logger(f"[WEATHER] Pruned old archive (count) {p}")
            except Exception:
                pass

    except Exception as e:
        if logger:
            logger(f"[WEATHER] Cleanup archive error {type(e).__name__}: {e}")


def housekeeping(app_dir: str, logger=None) -> None:
    current, archive = _cache_paths(app_dir)

    # Se não há diretório gravável (TV/pendrive bloqueado), não faz housekeeping.
    if not current or not archive:
        return

    _cleanup_cache_archive(archive, logger=logger)

    # remove tmp velho se existir
    try:
        tmp = current + ".tmp"
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception:
        pass

    # Limpeza periódica de ícones antigos (evita crescimento infinito do cache de PNG).
    try:
        icons = _icons_dir(app_dir)
        if not icons or not os.path.isdir(icons):
            return

        now = time.time()
        max_age = ICON_STALE_DAYS * 86400
        if max_age <= 0:
            return

        for name in os.listdir(icons):
            p = os.path.join(icons, name)
            if not os.path.isfile(p):
                continue
            try:
                st = os.stat(p)
            except Exception:
                continue
            if (now - st.st_mtime) > max_age:
                try:
                    os.remove(p)
                    if logger:
                        logger(f"[WEATHER] Pruned old icon {p}")
                except Exception:
                    pass
    except Exception:
        pass


# ============================================================
# net (SSL/HTTP) – tolerante a ambiente corporativo (proxy + trust store)
# ============================================================

def _ssl_context_best_effort() -> ssl.SSLContext:
    try:
        import truststore  # type: ignore
        truststore.inject_into_ssl()
        return ssl.create_default_context()
    except Exception:
        pass

    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass

    return ssl.create_default_context()


def _build_opener(logger=None) -> urllib.request.OpenerDirector:
    proxies: Dict[str, str] = {}

    try:
        p_env = urllib.request.getproxies() or {}
        proxies.update({k.lower(): v for k, v in p_env.items() if v})
    except Exception:
        pass

    try:
        getproxies_registry = getattr(urllib.request, "getproxies_registry", None)
        if callable(getproxies_registry):
            p_reg_obj = getproxies_registry()
            if isinstance(p_reg_obj, dict):
                proxies.update({k.lower(): v for k, v in p_reg_obj.items() if v})
    except Exception:
        pass

    if logger:
        logger(f"[WEATHER] Proxies detectados: {proxies if proxies else 'nenhum'}")

    proxy_handler = urllib.request.ProxyHandler(proxies) if proxies else urllib.request.ProxyHandler({})
    https_handler = urllib.request.HTTPSHandler(context=_ssl_context_best_effort())
    return urllib.request.build_opener(proxy_handler, https_handler)


def _http_get_bytes(url: str, user_agent: str, timeout: int = 8, logger=None) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "*/*"},
        method="GET",
    )

    opener = _build_opener(logger=logger)

    last_exc: Optional[Exception] = None
    for attempt in (1, 2):
        try:
            if logger:
                logger(f"[WEATHER] GET bytes attempt {attempt} timeout={timeout}s url={url}")
            with opener.open(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            last_exc = e
            if logger:
                logger(f"[WEATHER] GET bytes error {type(e).__name__}: {e}")
            if attempt == 1:
                time.sleep(0.4)
                continue
            raise
    raise last_exc if last_exc else RuntimeError("HTTP bytes failed")


def _http_get_json(url: str, user_agent: str, timeout: int = 6, logger=None) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
        method="GET",
    )

    opener = _build_opener(logger=logger)

    last_exc: Optional[Exception] = None
    for attempt in (1, 2):
        try:
            if logger:
                logger(f"[WEATHER] HTTP attempt {attempt} timeout={timeout}s")
            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                if logger:
                    status = getattr(resp, "status", None) or getattr(resp, "code", "?")
                    logger(f"[WEATHER] HTTP {status} len={len(raw)}")
                return json.loads(raw)

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read(200).decode("utf-8", errors="replace")
            except Exception:
                pass
            if logger:
                logger(f"[WEATHER] HTTPError {e.code} {e.reason} body='{body}'")
            raise

        except urllib.error.URLError as e:
            last_exc = e
            if logger:
                logger(f"[WEATHER] URLError reason={repr(getattr(e, 'reason', e))}")
            if attempt == 1:
                time.sleep(0.4)
                continue
            raise

        except Exception as e:
            last_exc = e
            if logger:
                logger(f"[WEATHER] Exception {type(e).__name__}: {e}")
            if attempt == 1:
                time.sleep(0.4)
                continue
            raise

    raise last_exc if last_exc else RuntimeError("HTTP failed")

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
      %LOCALAPPDATA%\\CLUBAL_Agenda_Live\\package\\weather_icons\\<symbol_code>.png

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
            logger(f"[WEATHER] Icon miss (no symbol_code)")
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

            tmp = local_path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, local_path)

            if logger:
                logger(f"[WEATHER] Icon cached -> {local_path}")
            return local_path

        except Exception as e:
            if logger:
                logger(f"[WEATHER] Icon download failed code={code_base} err={type(e).__name__}: {e}")

            try:
                tmp = local_path + ".tmp"
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

            # tenta o próximo candidato
            continue

    return None

# ============================================================
# icon pack prewarm (background) – baixa um conjunto amplo de ícones
# ============================================================

_PREWARM_LOCK = threading.Lock()
_PREWARM_STARTED = False


def _icon_pack_codes_full() -> list[str]:
    """
    Lista ampla (mas segura) de códigos de ícones do metno/weathericons.

    Observação:
    - Alguns códigos têm variações _day/_night.
    - Outros não têm sufixo (ex.: cloudy, fog, heavyrain).
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

            # Marca diária (evita ficar baixando sempre no boot)
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
                    tmp = p + ".tmp"
                    with open(tmp, "wb") as f:
                        f.write(data)
                    os.replace(tmp, p)
                    downloaded += 1
                    if logger:
                        logger(f"[WEATHER] Prewarm cached -> {p}")
                except Exception:
                    try:
                        tmp = p + ".tmp"
                        if os.path.exists(tmp):
                            os.remove(tmp)
                    except Exception:
                        pass

            # grava stamp do dia (mesmo se baixou 0, para evitar loop de tentativas em rede ruim)
            try:
                _write_json_atomic(stamp_path, {"day": today_key, "downloaded": int(downloaded), "ts": int(time.time())})
            except Exception:
                pass

            if logger:
                logger(f"[WEATHER] Prewarm done downloaded={downloaded} day={today_key}")

        except Exception as e:
            if logger:
                logger(f"[WEATHER] Prewarm error {type(e).__name__}: {e}")

    t = threading.Thread(target=_worker, name="weather_icon_prewarm", daemon=True)
    t.start()

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