from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .environment import Environment


APP_ROOT_NAME = "CLUBAL_Agenda_Live"
PORTABLE_ROOT_PARENT = "_data"

# Cria um "atalho de pasta" (junction) para facilitar achar logs/cache rápido.
# Fica dentro do __pycache__ (pode ser apagado e será recriado no próximo run).
RUNTIME_LINK_PARENT = "__pycache__"
RUNTIME_LINK_NAME = "_CLUBAL_DATA"


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

        # Já existe -> não mexe
        if link_path.exists():
            return

        # Garante pai
        try:
            link_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            return

        # mklink /J <link> <target>
        cmd = ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        return


def _ensure_runtime_link_best_effort(app_dir: Path, writable_root: Path | None) -> None:
    """
    Cria um link local (junction) para a pasta gravável (logs/cache) dentro de:
      <app_dir>/__pycache__/_CLUBAL_DATA  ->  <writable_root>

    Se não houver writable_root, não faz nada.
    """
    try:
        if writable_root is None:
            return

        parent = app_dir / RUNTIME_LINK_PARENT
        if not _ensure_dir_best_effort(parent):
            return

        link_path = parent / RUNTIME_LINK_NAME
        _create_junction_best_effort(link_path, writable_root)
    except Exception:
        return


def build_paths(env: Environment) -> Paths:
    app_dir = env.app_dir

    # Onde ficam assets fixos (imagens etc.)
    assets_dir = app_dir / "graphics"

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
    # logs: <root>\logs
    # package: <root>\package   (weather_cache.json, cache_old, weather_icons)
    if writable_root is not None:
        ld = writable_root / "logs"
        pd = writable_root / "package"

        if _ensure_dir_best_effort(ld):
            logs_dir = ld
        if _ensure_dir_best_effort(pd):
            cache_dir = pd

    # Atalho local para facilitar achar logs/cache (best-effort)
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
    Subpastas dentro do 'package' (ex.: cache_old, weather_icons, etc.)
    """
    if paths.cache_dir is None:
        return None
    p = paths.cache_dir / name
    if _ensure_dir_best_effort(p):
        return p
    return None