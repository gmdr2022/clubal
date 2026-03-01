from __future__ import annotations

from datetime import datetime


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def remaining_progress(now_dt: datetime, start_dt: datetime, end_dt: datetime) -> float:
    """
    Barra do card AGORA:
    cheia no início, esvaziando até o fim.
    """
    total = (end_dt - start_dt).total_seconds()
    done = (now_dt - start_dt).total_seconds()

    if total <= 0:
        return 0.0

    remaining = total - done
    return clamp01(remaining / total)


def upcoming_progress(now_dt: datetime, start_dt: datetime, window_end: datetime, floor: float = 0.02) -> float:
    """
    Barra do card PRÓXIMAS:
    mais cheia quando falta mais tempo para começar.
    """
    total_win = (window_end - now_dt).total_seconds()
    remaining = (start_dt - now_dt).total_seconds()

    if total_win <= 0:
        base = 0.0
    else:
        base = clamp01(remaining / total_win)

    return max(float(floor), base)


def minutes_until(now_dt: datetime, target_dt: datetime) -> int:
    return int(max(0, round((target_dt - now_dt).total_seconds() / 60.0)))