from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .environment import Environment


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
        root = env.localappdata / "CLUBAL_Agenda_Live"
        if _writable_dir_probe(root):
            writable_root = root

    else:
        # Portable (pendrive/TV): tenta ao lado do app em _data\CLUBAL_Agenda_Live
        root = app_dir / "_data" / "CLUBAL_Agenda_Live"
        if _writable_dir_probe(root):
            writable_root = root

    # Estrutura padronizada (igual ao weather_service.py)
    # logs: <root>\logs
    # cache/package: <root>\package   (weather_cache.json, cache_old, weather_icons)
    if writable_root is not None:
        ld = writable_root / "logs"
        pd = writable_root / "package"

        if _ensure_dir_best_effort(ld):
            logs_dir = ld
        if _ensure_dir_best_effort(pd):
            cache_dir = pd

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