from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from typing import Callable, List, Optional, Tuple

from .models import ClassItem


DAY_ALIASES = {
    "SEG": "MON",
    "TER": "TUE",
    "QUA": "WED",
    "QUI": "THU",
    "SEX": "FRI",
    "SAB": "SAT",
    "SÁB": "SAT",
    "DOM": "SUN",
}


_EN_WEEKDAY_INDEX = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}


def _debug_enabled() -> bool:
    try:
        return str(os.environ.get("CLUBAL_DEBUG_AGENDA", "0")).strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return False


def normalize_day_code(day: str) -> str:
    d = (day or "").strip().upper()
    d = d.replace(".", "")
    d = d.replace("Ç", "C")
    d = d.replace("Á", "A").replace("Ã", "A").replace("Â", "A")
    d = d.replace("É", "E").replace("Ê", "E")
    d = d.replace("Í", "I")
    d = d.replace("Ó", "O").replace("Õ", "O").replace("Ô", "O")
    d = d.replace("Ú", "U")

    d3 = d[:3]
    return DAY_ALIASES.get(d3, d3)


def _best_date_for_daycode(now_dt: datetime, day_code_raw: str) -> Optional[date]:
    """
    Replica a lógica antiga do clubal.py:
    procura o dia correspondente entre ontem / hoje / amanhã.
    Isso é importante para itens cross-midnight e encaixes próximos da virada.
    """
    code = normalize_day_code(day_code_raw)
    if code not in _EN_WEEKDAY_INDEX:
        return None

    target_idx = _EN_WEEKDAY_INDEX[code]
    candidates = [
        now_dt.date() - timedelta(days=1),
        now_dt.date(),
        now_dt.date() + timedelta(days=1),
    ]

    for d in candidates:
        if d.weekday() == target_idx:
            return d

    return now_dt.date()


def _parse_time_obj(value: str) -> Optional[time]:
    s = (value or "").strip()
    if not s:
        return None

    parts = s.split(":")
    try:
        if len(parts) == 2:
            hh = int(parts[0])
            mm = int(parts[1])
            ss = 0
        elif len(parts) >= 3:
            hh = int(parts[0])
            mm = int(parts[1])
            ss = int(parts[2])
        else:
            return None

        if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
            return None

        return time(hour=hh, minute=mm, second=ss)
    except Exception:
        return None


def item_interval_debug(
    now_dt: datetime,
    it: ClassItem,
    log_fn: Optional[Callable[[str], None]] = None,
) -> Tuple[Optional[Tuple[datetime, datetime]], str]:
    """
    Replica a lógica atual de debug:
    - resolve base_date via day_code
    - parse time robusto
    - se end <= start, considera cross-midnight e soma 1 dia
    - log opcional controlado por env var
    """
    base_date = _best_date_for_daycode(now_dt, it.day)
    if base_date is None:
        return None, "invalid_day"

    t_start = _parse_time_obj(it.start)
    t_end = _parse_time_obj(it.end)
    if t_start is None or t_end is None:
        if log_fn is not None and _debug_enabled():
            try:
                log_fn(f"[AGENDA][TIME_PARSE_FAIL] day={it.day} start_raw={repr(it.start)} end_raw={repr(it.end)}")
            except Exception:
                pass
        return None, "invalid_time"

    start_dt = datetime.combine(base_date, t_start)
    end_dt = datetime.combine(base_date, t_end)

    if end_dt <= start_dt:
        end_dt = end_dt + timedelta(days=1)
        if log_fn is not None and _debug_enabled():
            try:
                log_fn(
                    "[AGENDA][CROSS_MIDNIGHT] "
                    f"item=({it.day} {it.start}->{it.end} {it.modalidade} tag={it.tag}) "
                    f"start={start_dt.strftime('%Y-%m-%d %H:%M:%S')} end={end_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception:
                pass

    return (start_dt, end_dt), "ok"


def compute_now_next(
    now_dt: datetime,
    all_items: List[ClassItem],
    window_minutes: int = 120,
    log_fn: Optional[Callable[[str], None]] = None,
) -> Tuple[List[Tuple], List[Tuple], int, int, int]:
    """
    Retorna:
      - now_list: [(it, start_dt, end_dt), ...]
      - next_list: [(it, start_dt, end_dt), ...]
      - discard_day, discard_time, discard_other
    Mantém compatibilidade com a lógica antiga de debug/contadores.
    """
    window_end = now_dt + timedelta(minutes=int(window_minutes))

    now_list: List[Tuple] = []
    next_list: List[Tuple] = []

    discard_day = 0
    discard_time = 0
    discard_other = 0

    for it in all_items:
        interval, reason = item_interval_debug(now_dt, it, log_fn=log_fn)
        if not interval:
            if reason == "invalid_day":
                discard_day += 1
            elif reason == "invalid_time":
                discard_time += 1
            else:
                discard_other += 1
            continue

        start_dt, end_dt = interval

        if start_dt <= now_dt < end_dt:
            now_list.append((it, start_dt, end_dt))
        elif now_dt < start_dt <= window_end:
            next_list.append((it, start_dt, end_dt))

    now_list.sort(key=lambda x: x[1])
    next_list.sort(key=lambda x: x[1])

    return now_list, next_list, discard_day, discard_time, discard_other