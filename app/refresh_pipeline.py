from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, List, Optional, Tuple

import weather_service as weather_mod
from core.agenda import compute_now_next as agenda_compute_now_next
from core.card_metrics import minutes_until, remaining_progress, upcoming_progress
from core.models import ClassItem
from core.time_utils import split_clock_hhmm_ss
from infra.xlsx_loader import (
    XLSX_STATE_ERROR,
    XLSX_STATE_MISSING,
    XLSX_STATE_OK,
    reload_classes_if_needed,
)

WEATHER_CITY_LABEL = "Alfenas"
WEATHER_LAT = -21.4267
WEATHER_LON = -45.9470
WEATHER_MIN_REFRESH_SEC = 600
WEATHER_USER_AGENT = "CLUBAL-AgendaLive/2.0 (contact: local)"

EXCEL_MISSING_MSG_AGORA = "PLANILHA LOCAL AUSENTE\nCOLOQUE grade.xlsx AO LADO DO APP"
EXCEL_MISSING_MSG_PROX = "USE grade_template.xlsx\nCOMO MODELO"
EXCEL_ERROR_MSG_AGORA = "ERRO AO LER grade.xlsx"
EXCEL_ERROR_MSG_PROX = "REVISE A ABA CLUBAL\nE OS CABEÇALHOS"


def _set_section_empty_override(section: Any, text: str | None) -> None:
    if section is None:
        return

    try:
        fn = getattr(section, "set_empty_override", None)
        if callable(fn):
            fn(text)
    except Exception:
        pass


def _clear_agenda_empty_overrides(app: Any) -> None:
    _set_section_empty_override(getattr(app, "agora", None), None)
    _set_section_empty_override(getattr(app, "prox", None), None)


def _apply_excel_ui_state(app: Any) -> bool:
    state = str(getattr(app, "_excel_load_state", XLSX_STATE_OK) or XLSX_STATE_OK).strip().lower()

    if state == XLSX_STATE_MISSING:
        _set_section_empty_override(getattr(app, "agora", None), EXCEL_MISSING_MSG_AGORA)
        _set_section_empty_override(getattr(app, "prox", None), EXCEL_MISSING_MSG_PROX)
        app.agora.update_cards([])
        app.prox.update_cards([])
        return True

    if state == XLSX_STATE_ERROR:
        _set_section_empty_override(getattr(app, "agora", None), EXCEL_ERROR_MSG_AGORA)
        _set_section_empty_override(getattr(app, "prox", None), EXCEL_ERROR_MSG_PROX)
        app.agora.update_cards([])
        app.prox.update_cards([])
        return True

    _clear_agenda_empty_overrides(app)
    return False


def reload_excel_if_needed(
    excel_path: str,
    all_items: List[ClassItem],
    last_excel_mtime: Optional[float],
    *,
    force: bool = False,
    logger=None,
) -> Tuple[List[ClassItem], Optional[float], bool, str]:
    return reload_classes_if_needed(
        excel_path,
        all_items,
        last_excel_mtime,
        force=force,
        logger=logger,
    )


def reload_excel_state_if_needed(
    app: Any,
    *,
    excel_path: str,
    force: bool = False,
    logger=None,
) -> None:
    prev_state = str(getattr(app, "_excel_load_state", XLSX_STATE_OK) or XLSX_STATE_OK).strip().lower()

    app.all_items, app.last_excel_mtime, changed, state = reload_excel_if_needed(
        excel_path,
        app.all_items,
        app.last_excel_mtime,
        force=force,
        logger=logger,
    )

    app._excel_load_state = state

    if changed or state != prev_state:
        app._last_agenda_run_ts = 0.0


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


def fetch_weather_result(
    app_dir: str,
    *,
    city_label: str = WEATHER_CITY_LABEL,
    lat: float = WEATHER_LAT,
    lon: float = WEATHER_LON,
    user_agent: str = WEATHER_USER_AGENT,
    logger: Optional[Callable[[str], None]] = None,
) -> weather_mod.WeatherResult:
    return weather_mod.get_weather(
        city_label=city_label,
        lat=lat,
        lon=lon,
        app_dir=app_dir,
        user_agent=user_agent,
        logger=logger,
    )


def _weather_worker(
    app: Any,
    *,
    app_dir: str,
    city_label: str = WEATHER_CITY_LABEL,
    lat: float = WEATHER_LAT,
    lon: float = WEATHER_LON,
    user_agent: str = WEATHER_USER_AGENT,
    logger: Optional[Callable[[str], None]] = None,
) -> None:
    try:
        res = fetch_weather_result(
            app_dir=app_dir,
            city_label=city_label,
            lat=lat,
            lon=lon,
            user_agent=user_agent,
            logger=logger,
        )
        with app._weather_lock:
            app.weather_res = res
            app.weather_last_fetch = time.time()
    except Exception as e:
        if logger:
            logger(f"[WEATHER] Worker error {type(e).__name__}: {e}")
    finally:
        with app._weather_lock:
            app._weather_inflight = False


def tick_weather_refresh(
    app: Any,
    *,
    app_dir: str,
    city_label: str = WEATHER_CITY_LABEL,
    lat: float = WEATHER_LAT,
    lon: float = WEATHER_LON,
    user_agent: str = WEATHER_USER_AGENT,
    min_interval_sec: int = WEATHER_MIN_REFRESH_SEC,
    logger: Optional[Callable[[str], None]] = None,
) -> None:
    if (time.time() - app.weather_last_fetch) < min_interval_sec and app.weather_res is not None:
        return

    with app._weather_lock:
        if app._weather_inflight:
            return
        app._weather_inflight = True

    th = threading.Thread(
        target=_weather_worker,
        kwargs={
            "app": app,
            "app_dir": app_dir,
            "city_label": city_label,
            "lat": lat,
            "lon": lon,
            "user_agent": user_agent,
            "logger": logger,
        },
        daemon=True,
    )
    th.start()


def build_weather_ui_key(res: Any) -> Tuple[Any, ...]:
    return (
        getattr(res, "ok", None),
        getattr(res, "source", None),
        getattr(res, "temp_c", None),
        getattr(res, "symbol_code", None),
        getattr(res, "today_label", None),
        getattr(res, "tomorrow_label", None),
        getattr(res, "cache_ts", None),
    )


def apply_weather_result_if_changed(
    app: Any,
    *,
    city_label: str = WEATHER_CITY_LABEL,
) -> None:
    with app._weather_lock:
        res = app.weather_res

    if not res:
        return

    key = build_weather_ui_key(res)
    if key == app._last_weather_ui_key:
        return

    app._last_weather_ui_key = key
    app.weather_card.set_weather(city_label, res)


def refresh_agenda_if_due(
    app: Any,
    *,
    min_interval_sec: int = 15,
    logger: Optional[Callable[[str], None]] = None,
) -> None:
    if time.time() - app._last_agenda_run_ts < min_interval_sec:
        return

    app._last_agenda_run_ts = time.time()

    if _apply_excel_ui_state(app):
        return

    now_dt = datetime.now()
    now_cards, next_cards, _window_end, _discard_day, _discard_time, _discard_other = compute_now_next_cards(
        now_dt=now_dt,
        all_items=app.all_items,
        window_minutes=120,
        log_fn=logger,
    )

    app.agora.update_cards(now_cards)
    app.prox.update_cards(next_cards)


def refresh_header_clock_and_hours(
    app: Any,
    *,
    time_text: str,
    now_struct: Any = None,
) -> None:
    app._update_datecard_text_adaptive()

    hhmm, ss = split_clock_hhmm_ss(time_text)
    if hasattr(app, "time_hhmm_lbl"):
        app.time_hhmm_lbl.configure(text=hhmm)
    if hasattr(app, "time_ss_lbl"):
        app.time_ss_lbl.configure(text=f":{ss}")

    if now_struct is None:
        now_struct = time.localtime()

    minute_key = (
        now_struct.tm_wday,
        now_struct.tm_hour,
        now_struct.tm_min,
        getattr(app.hours_card, "_mode", 0),
    )
    if minute_key == app._last_hours_minute_key:
        return

    app._last_hours_minute_key = minute_key
    app.hours_card.update_view(force=False)


def handle_theme_rebuild_if_needed(
    app: Any,
    *,
    new_theme_is_day: bool,
    excel_path: str,
    logger: Optional[Callable[[str], None]] = None,
) -> bool:
    if new_theme_is_day == app.is_day_theme:
        return False

    app._apply_theme()
    app._build_ui()
    reload_excel_state_if_needed(
        app,
        excel_path=excel_path,
        force=True,
        logger=logger,
    )
    app._last_weather_ui_key = None
    app._last_agenda_run_ts = 0.0
    app._last_hours_minute_key = None
    return True