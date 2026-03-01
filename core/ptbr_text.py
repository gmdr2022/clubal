from __future__ import annotations

import time


def weekday_full_ptbr() -> str:
    wd = time.localtime().tm_wday  # Monday=0
    return [
        "SEGUNDA-FEIRA",
        "TERÇA-FEIRA",
        "QUARTA-FEIRA",
        "QUINTA-FEIRA",
        "SEXTA-FEIRA",
        "SÁBADO",
        "DOMINGO",
    ][wd]


def weekday_short_ptbr() -> str:
    wd = time.localtime().tm_wday  # Monday=0
    return [
        "Segunda",
        "Terça",
        "Quarta",
        "Quinta",
        "Sexta",
        "Sábado",
        "Domingo",
    ][wd]


def weekday_abbr_ptbr() -> str:
    wd = time.localtime().tm_wday  # Monday=0
    return [
        "Seg",
        "Ter",
        "Qua",
        "Qui",
        "Sex",
        "Sáb",
        "Dom",
    ][wd]


def month_name_ptbr(month_num: int) -> str:
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril",
        "Maio", "Junho", "Julho", "Agosto",
        "Setembro", "Outubro", "Novembro", "Dezembro",
    ]
    if 1 <= month_num <= 12:
        return meses[month_num - 1]
    return "Mês"


def month_abbr_ptbr(month_num: int) -> str:
    meses = [
        "Jan", "Fev", "Mar", "Abr",
        "Mai", "Jun", "Jul", "Ago",
        "Set", "Out", "Nov", "Dez",
    ]
    if 1 <= month_num <= 12:
        return meses[month_num - 1]
    return "Mês"


def formal_date_line_ptbr() -> str:
    lt = time.localtime()
    wd = weekday_full_ptbr()
    dd = lt.tm_mday
    mm = month_name_ptbr(lt.tm_mon)
    yy = lt.tm_year
    return f"{wd} • {dd} de {mm} de {yy}"