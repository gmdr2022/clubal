from __future__ import annotations

import time
from typing import Any, Callable, Optional

import weather_service as weather_mod
from infra.logging_manager import rotate_logs_if_needed

from app.refresh_pipeline import (
    apply_weather_result_if_changed,
    handle_theme_rebuild_if_needed,
    refresh_agenda_if_due,
    refresh_header_clock_and_hours,
    reload_excel_state_if_needed,
    tick_weather_refresh,
)


def tick_housekeeping_if_due(
    app: Any,
    *,
    log_path: Optional[str],
    log_archive_dir: Optional[str],
    app_dir: str,
    logger: Optional[Callable[[str], None]] = None,
    min_interval_sec: int = 86400,
) -> None:
    if time.time() - app._last_housekeeping_ts < min_interval_sec:
        return

    app._last_housekeeping_ts = time.time()

    try:
        if log_path and log_archive_dir:
            rotate_logs_if_needed(log_path, log_archive_dir, logger=logger)

        weather_mod.housekeeping(app_dir=app_dir, logger=logger)
    except Exception as e:
        if logger:
            logger(f"[HK] error {type(e).__name__}: {e}")


def schedule_next_tick(
    app: Any,
    tick_callback,
    *,
    delay_ms: int = 1000,
) -> None:
    app.after(delay_ms, tick_callback)


def run_tick_cycle(
    app: Any,
    *,
    new_theme_is_day: bool,
    time_text: str,
    excel_path: str,
    app_dir: str,
    log_path: Optional[str],
    log_archive_dir: Optional[str],
    logger: Optional[Callable[[str], None]] = None,
) -> None:
    handle_theme_rebuild_if_needed(
        app,
        new_theme_is_day=new_theme_is_day,
        excel_path=excel_path,
        logger=logger,
    )

    refresh_header_clock_and_hours(
        app,
        time_text=time_text,
    )

    reload_excel_state_if_needed(
        app,
        excel_path=excel_path,
        force=False,
        logger=logger,
    )

    refresh_agenda_if_due(
        app,
        min_interval_sec=15,
        logger=logger,
    )

    tick_weather_refresh(
        app,
        app_dir=app_dir,
        logger=logger,
    )

    apply_weather_result_if_changed(
        app,
        city_label="Alfenas",
    )

    tick_housekeeping_if_due(
        app,
        log_path=log_path,
        log_archive_dir=log_archive_dir,
        app_dir=app_dir,
        logger=logger,
        min_interval_sec=86400,
    )