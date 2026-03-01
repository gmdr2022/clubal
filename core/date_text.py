from __future__ import annotations

import time
from typing import List, Tuple

from core.ptbr_text import (
    month_abbr_ptbr,
    month_name_ptbr,
    weekday_abbr_ptbr,
    weekday_full_ptbr,
    weekday_short_ptbr,
)


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


def build_datecard_candidates_ptbr() -> List[str]:
    lt = time.localtime()

    wd_full = weekday_full_ptbr()
    wd_title = wd_full.title()
    wd_short = weekday_short_ptbr()
    wd_abbr = weekday_abbr_ptbr()

    dd = lt.tm_mday
    mm_full = month_name_ptbr(lt.tm_mon)
    mm_abbr = month_abbr_ptbr(lt.tm_mon)
    yy = lt.tm_year

    cands = [
        f"{wd_full}  •  {dd} de {mm_full} de {yy}",
        f"{wd_title}  •  {dd} de {mm_full} de {yy}",
        f"{wd_short}  •  {dd} de {mm_full} de {yy}",
        f"{wd_short}  •  {dd} de {mm_abbr} de {yy}",
        f"{wd_short}  •  {dd} de {mm_abbr}",
        f"{wd_abbr}  •  {dd} de {mm_abbr}",
        f"{wd_abbr}  •  {dd} {mm_abbr}",
        f"{wd_abbr} {dd} {mm_abbr}",
    ]

    seen = set()
    out: List[str] = []

    for s in cands:
        if s not in seen:
            seen.add(s)
            out.append(s)

    return out