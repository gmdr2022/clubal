from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Environment:
    is_windows: bool
    mode: str  # "installed" | "portable"
    app_dir: Path
    localappdata: Path | None


def _is_windows() -> bool:
    return os.name == "nt"


def _app_dir() -> Path:
    """
    Diretório base do app.
    - Em modo normal: pasta do repo (um nível acima de core/)
    - Em modo frozen (EXE): pasta do executável
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _localappdata_dir() -> Path | None:
    p = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if not p:
        return None
    try:
        return Path(p).resolve()
    except Exception:
        return None


def _writable_dir_probe(base: Path) -> bool:
    """
    Teste best-effort de escrita.
    Nunca lança erro fatal.
    """
    try:
        base.mkdir(parents=True, exist_ok=True)
        probe = base / ".__clubal_write_probe__"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)  # py3.8+ ok no Windows
        return True
    except Exception:
        return False


def detect_environment() -> Environment:
    app_dir = _app_dir()
    is_win = _is_windows()
    la = _localappdata_dir() if is_win else None

    # Forçar portable por flag
    forced_portable = False
    if os.environ.get("CLUBAL_PORTABLE", "").strip() in ("1", "true", "True", "YES", "yes"):
        forced_portable = True
    if (app_dir / "PORTABLE_MODE").exists():
        forced_portable = True

    mode = "portable"
    if not forced_portable and is_win and la is not None:
        # installed só se conseguir escrever em LOCALAPPDATA
        if _writable_dir_probe(la / "CLUBAL"):
            mode = "installed"

    return Environment(
        is_windows=is_win,
        mode=mode,
        app_dir=app_dir,
        localappdata=la,
    )