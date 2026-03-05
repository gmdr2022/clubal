from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Tuple

from core.environment import detect_environment
from core.paths import build_paths, cache_subdir

__all__ = [
    "CACHE_ARCHIVE_DIRNAME",
    "CACHE_ARCHIVE_KEEP",
    "CACHE_ARCHIVE_MAX_AGE_DAYS",
    "ICONS_DIRNAME",
    "ICON_STALE_DAYS",
    "_safe_int",
    "_safe_mkdir",
    "_read_json",
    "_write_json_atomic",
    "_cache_root",
    "_cache_paths",
    "_icons_dir",
    "_archive_existing_cache",
    "_cleanup_cache_archive",
    "housekeeping",
]

_ENV = detect_environment()
_PATHS = build_paths(_ENV)


# ============================================================
# cache policy / housekeeping
# ============================================================

CACHE_ARCHIVE_DIRNAME = "cache_old"
CACHE_ARCHIVE_KEEP = 10                 # mantém últimos N caches antigos
CACHE_ARCHIVE_MAX_AGE_DAYS = 7          # apaga cache_old com mais de N dias

ICONS_DIRNAME = "weather_icons"         # cache dos PNGs oficiais
ICON_STALE_DAYS = 60                    # (opcional) rebaixar se quiser (não obrigatório)


# ============================================================
# cache_io helpers
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