from __future__ import annotations

from dataclasses import dataclass

from .environment import Environment, detect_environment
from .paths import Paths, build_paths


@dataclass(frozen=True)
class BootstrapContext:
    env: Environment
    paths: Paths


def bootstrap() -> BootstrapContext:
    """
    Bootstrap mínimo:
    - detecta ambiente
    - resolve paths
    - NÃO cria nada fora do necessário
    - nunca falha por permissão (paths pode vir com logs/cache = None)
    """
    env = detect_environment()
    paths = build_paths(env)
    return BootstrapContext(env=env, paths=paths)