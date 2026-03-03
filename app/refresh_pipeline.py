from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from core.agenda import compute_now_next as agenda_compute_now_next
from core.card_metrics import minutes_until, remaining_progress, upcoming_progress
from core.models import ClassItem
from infra.xlsx_loader import reload_classes_if_needed


def reload_excel_if_needed(
    excel_path: str,
    all_items: List[ClassItem],
    last_excel_mtime: Optional[float],
    *,
    force: bool = False,
    logger=None,
) -> Tuple[List[ClassItem], Optional[float]]:
    all_items, last_excel_mtime, _changed = reload_classes_if_needed(
        excel_path,
        all_items,
        last_excel_mtime,
        force=force,
        logger=logger,
    )
    return all_items, last_excel_mtime


def compute_now_next_cards(
    now_dt: datetime,
    all_items: List[ClassItem],
    *,
    window_minutes: int = 120,
    log_fn=None,
) -> Tuple[List[Tuple], List[Tuple], datetime, int, int, int]:
    window_end = now_dt + timedelta(minutes=window_minutes)

    now_list, next_list, discard_day, discard_time, discard_other = agenda_compute_now_next(
        now_dt=now_dt,
        all_items=all_items,
        window_minutes=window_minutes,
        log_fn=log_fn,
    )

    now_cards = []
    for it, start_dt, end_dt in now_list:
        progress = remaining_progress(now_dt, start_dt, end_dt)
        mins_left = minutes_until(now_dt, end_dt)
        now_cards.append(
            (
                it.start,
                it.end,
                it.modalidade,
                it.professor,
                "",
                it.tag,
                progress,
                mins_left,
            )
        )

    next_cards = []
    for it, start_dt, end_dt in next_list:
        progress_next = upcoming_progress(now_dt, start_dt, window_end)
        mins_to_start = minutes_until(now_dt, start_dt)
        next_cards.append(
            (
                it.start,
                it.end,
                it.modalidade,
                it.professor,
                "",
                it.tag,
                progress_next,
                mins_to_start,
            )
        )

    return now_cards, next_cards, window_end, discard_day, discard_time, discard_other