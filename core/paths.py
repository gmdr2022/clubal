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

    # Onde ficam dados do app (grade.xlsx etc.) — no repo/na pasta do exe
    data_dir = app_dir

    writable_root: Path | None = None
    logs_dir: Path | None = None
    cache_dir: Path | None = None

    if env.mode == "installed" and env.localappdata is not None:
        root = env.localappdata / "CLUBAL"
        if _ensure_dir_best_effort(root):
            writable_root = root
    else:
        # portable: tenta escrever ao lado do app (pendrive), mas pode falhar
        root = app_dir / "_data"
        if _ensure_dir_best_effort(root):
            writable_root = root

    if writable_root is not None:
        ld = writable_root / "logs"
        cd = writable_root / "cache"
        if _ensure_dir_best_effort(ld):
            logs_dir = ld
        if _ensure_dir_best_effort(cd):
            cache_dir = cd

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
    if paths.cache_dir is None:
        return None
    p = paths.cache_dir / name
    if _ensure_dir_best_effort(p):
        return p
    return None