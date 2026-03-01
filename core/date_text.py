from __future__ import annotations

import time
from typing import Tuple


def today_3letters_noaccent() -> str:
    wd = time.localtime().tm_wday  # Monday=0
    return ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"][wd]


def weekday_full_noaccent() -> str:
    wd = time.localtime().tm_wday
    return [
        "SEGUNDA-FEIRA",
        "TERCA-FEIRA",
        "QUARTA-FEIRA",
        "QUINTA-FEIRA",
        "SEXTA-FEIRA",
        "SABADO",
        "DOMINGO",
    ][wd]


def date_time_strings() -> Tuple[str, str, str]:
    lt = time.localtime()
    date_s = time.strftime("%d/%m/%Y", lt)
    time_s = time.strftime("%H:%M:%S", lt)
    wd_s = weekday_full_noaccent()
    return date_s, time_s, wd_s