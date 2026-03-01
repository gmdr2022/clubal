from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassItem:
    day: str
    start: str
    end: str
    modalidade: str
    professor: str
    tag: Optional[str] = None