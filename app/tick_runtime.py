from __future__ import annotations

import time
from typing import Any, Callable, Optional

import weather_service as weather_mod
from infra.logging_manager import rotate_logs_if_needed


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