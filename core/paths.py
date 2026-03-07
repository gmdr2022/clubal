from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .environment import Environment

APP_ROOT_NAME = "CLUBAL_Agenda_Live"
PORTABLE_ROOT_PARENT = "_data"

# Alias visual local para facilitar abrir logs/cache sem entrar no AppData.
# Fonte de verdade continua sendo writable_root / ctx.paths.*.
RUNTIME_LINK_NAME = "_runtime_link"

# Legado antigo: __pycache__/_CLUBAL_DATA
LEGACY_RUNTIME_LINK_PARENT = "__pycache__"
LEGACY_RUNTIME_LINK_NAME = "_CLUBAL_DATA"
INTERNAL_DIR_NAME = "_internal"


@dataclass(frozen=True)
class Paths:
    app_dir: Path
    mode: str  # "installed" | "portable"

    # Pode ser None se não der pra escrever (ex.: TV/pendrive bloqueado)
    writable_root: Path | None

    assets_dir: Path
    data_dir: Path

    logs_dir: Path | None
    cache_dir: Path | None


def _writable_dir_probe(base: Path) -> bool:
    """
    Teste real de escrita (cria pasta + grava .tmp).
    Retorna False se ambiente bloquear gravação.
    """
    try:
        base.mkdir(parents=True, exist_ok=True)
        probe = base / ".__clubal_write_probe__"
        probe.write_text("ok", encoding="utf-8")
        try:
            probe.unlink()
        except Exception:
            pass
        return True
    except Exception:
        return False


def _ensure_dir_best_effort(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def _create_junction_best_effort(link_path: Path, target_path: Path) -> None:
    """
    Windows junction (mklink /J) – best-effort: nunca quebra o app.
    """
    try:
        if os.name != "nt":
            return

        if link_path.exists():
            return

        try:
            link_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            return

        cmd = ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)]
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        return


def _remove_junction_best_effort(link_path: Path) -> None:
    """
    Remove uma junction/atalho legado sem tocar no destino real.
    Best-effort: nunca quebra o app.
    """
    try:
        if os.name != "nt":
            return

        if not link_path.exists():
            return

        try:
            os.rmdir(link_path)
            return
        except Exception:
            pass

        try:
            link_path.unlink()
        except Exception:
            pass
    except Exception:
        return

def _runtime_link_path(app_dir: Path) -> Path | None:
    """
    Alias local preferencial:
      <app_dir>/_internal/_runtime_link

    Regra:
    - só cria se _internal já existir
    - não cria _internal no projeto fonte
    """
    try:
        internal_dir = app_dir / INTERNAL_DIR_NAME
        if not internal_dir.exists() or not internal_dir.is_dir():
            return None
        return internal_dir / RUNTIME_LINK_NAME
    except Exception:
        return None

def _cleanup_legacy_runtime_link_best_effort(app_dir: Path) -> None:
    """
    Remove o alias legado __pycache__/_CLUBAL_DATA se ele ainda existir.
    """
    try:
        legacy_link = app_dir / LEGACY_RUNTIME_LINK_PARENT / LEGACY_RUNTIME_LINK_NAME
        _remove_junction_best_effort(legacy_link)
    except Exception:
        return


def _ensure_runtime_link_best_effort(app_dir: Path, writable_root: Path | None) -> None:
    """
    Cria um link local (junction) para a pasta gravável (logs/cache) em:
        /_runtime_link

    -> Se não houver writable_root, não faz nada.
    -> Depois tenta limpar o alias legado em __pycache__/_CLUBAL_DATA.
    """
    try:
        if writable_root is None:
            return

        link_path = _runtime_link_path(app_dir)
        if link_path is None:
            return
        _create_junction_best_effort(link_path, writable_root)
        _cleanup_legacy_runtime_link_best_effort(app_dir)
    except Exception:
        return


def _resolve_assets_dir(app_dir: Path) -> Path:
    """
    Resolve a pasta de assets com fallback para bundle PyInstaller.

    Prioridade:
    1) graphics/ ao lado do app/executável
    2) graphics/ dentro de sys._MEIPASS (one-file)
    3) fallback conservador: app_dir/graphics
    """
    external_assets_dir = app_dir / "graphics"
    if external_assets_dir.is_dir():
        return external_assets_dir

    try:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled_assets_dir = Path(str(meipass)).resolve() / "graphics"
            if bundled_assets_dir.is_dir():
                return bundled_assets_dir
    except Exception:
        pass

    return external_assets_dir


def build_paths(env: Environment) -> Paths:
    app_dir = env.app_dir

    # Onde ficam assets fixos (imagens etc.)
    assets_dir = _resolve_assets_dir(app_dir)

    # Onde ficam dados do app (grade.xlsx etc.)
    data_dir = app_dir

    writable_root: Path | None = None
    logs_dir: Path | None = None
    cache_dir: Path | None = None

    if env.mode == "installed" and env.localappdata is not None:
        # PC Windows (instalado): tudo vai para LOCALAPPDATA\CLUBAL_Agenda_Live
        root = env.localappdata / APP_ROOT_NAME
        if _writable_dir_probe(root):
            writable_root = root
    else:
        # Portable (pendrive/TV): tenta ao lado do app em _data\CLUBAL_Agenda_Live
        root = app_dir / PORTABLE_ROOT_PARENT / APP_ROOT_NAME
        if _writable_dir_probe(root):
            writable_root = root

    # Estrutura padronizada
    # logs: \logs
    # package: \package (weather_cache.json, cache_old, weather_icons)
    if writable_root is not None:
        ld = writable_root / "logs"
        pd = writable_root / "package"

        if _ensure_dir_best_effort(ld):
            logs_dir = ld

        if _ensure_dir_best_effort(pd):
            cache_dir = pd

    # Alias local para facilitar achar logs/cache (best-effort)
    _ensure_runtime_link_best_effort(app_dir, writable_root)

    return Paths(
        app_dir=app_dir,
        mode=env.mode,
        writable_root=writable_root,
        assets_dir=assets_dir,
        data_dir=data_dir,
        logs_dir=logs_dir,
        cache_dir=cache_dir,
    )


def cache_subdir(paths: Paths, name: str) -> Path | None:
    """
    Cria/retorna uma subpasta dentro do cache_dir gravável (installed/portable).

    Ex.: cache_subdir(paths, "weather") -> /weather
    """
    if paths.cache_dir is None:
        return None

    p = paths.cache_dir / name
    if _ensure_dir_best_effort(p):
        return p
    return None