
"""
CLUBAL – Club Agenda Live

App Tkinter em tela cheia para sinalização digital:
- Lê grade.xlsx (aba CLUBAL) e mostra AGORA/PRÓXIMAS com scroll contínuo.
- Mostra horários fixos (HoursCard) e clima (WeatherCard) com cache via weather_service.py.
- Registra logs em diretório gravável por usuário.

Estrutura do arquivo (candidato a divisão futura):
- Infra/IO: paths, logging, excel parsing, agenda compute
- UI widgets: RoundedFrame, ClassCard, SectionFrame, HoursCard, WeatherCard
- App: ClubalApp (build UI, ticks, theme, integração)
"""

from __future__ import annotations

import os
import sys
import time
import traceback
import threading
from dataclasses import dataclass
from core.models import ClassItem
from core.date_text import (
    build_datecard_candidates_ptbr,
    date_time_strings,
    today_3letters_noaccent,
    weekday_full_noaccent,
)
from core.time_utils import fmt_hhmm, parse_hhmm, split_clock_hhmm_ss

from core.ptbr_text import formal_date_line_ptbr
from core.card_metrics import minutes_until, remaining_progress, upcoming_progress
from core.agenda import compute_now_next as agenda_compute_now_next
from typing import Any, List, Optional, Tuple, Dict, cast

import tkinter as tk
import tkinter.font as tkfont

# garante que o root do projeto entre no sys.path quando este arquivo
# for executado diretamente a partir de app/clubal.py
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.bootstrap import bootstrap

from ui.theme import (
    SP_4,
    SP_8,
    SP_12,
    SP_16,
    SP_20,
    SP_24,
    SP_32,
    RADIUS_SM,
    RADIUS_MD,
    RADIUS_LG,
    SHADOW_SOFT,
    SHADOW_MD,
    MS_CARD_ROTATE,
    MS_SCROLL_TICK,
    MS_MARQUEE_TICK,
    MS_MARQUEE_SPEED_PX,
    MS_SECTION_SCROLL_SPEED_PX,
    MS_HOURS_ROTATE,
    theme_is_day,
    build_app_palette,
)

from infra.logging_manager import rotate_logs_if_needed, write_log
from ui.header_layout import calc_header_geometry
from ui.rounded_frame import RoundedFrame
from ui.image_runtime import (
    PIL_OK,
    PIL_LANCZOS,
    PIL_NEAREST,
    configure_image_search_dirs,
    first_image_in_dir as _first_image_in_dir,
    img_path_try as _img_path_try,
    pil_new_rgba as _pil_new_rgba,
    pil_open_rgba as _pil_open_rgba,
    pil_photo_image as _pil_photo_image,
)
from ui.content_sections import SectionFrame
from ui.content_cards import ClassCard
from ui.header_hours import HoursCard
from ui.header_weather import WeatherCard
from app.runtime_boot import (
    enable_windows_dpi_awareness,
    force_tk_scaling_96dpi,
    selftest_geometry,
)
from app.runtime_state import build_runtime_state
from app.main_ui_builder import build_main_ui
from app.main_ui_assets import (
    pil_contain_to_size,
    refresh_client_logo,
    refresh_logo,
)

from app.refresh_pipeline import (
    apply_weather_result_if_changed,
    compute_now_next_cards,
    handle_theme_rebuild_if_needed,
    refresh_agenda_if_due,
    refresh_header_clock_and_hours,
    reload_excel_if_needed,
    tick_weather_refresh,
)

from app.tick_runtime import tick_housekeeping_if_due

ctx = bootstrap()

from infra.xlsx_loader import reload_classes_if_needed

import weather_service as weather_mod

from datetime import datetime, timedelta, date as dt_date, time as dt_time

# Build ID para diagnóstico (logs).
CLUBAL_UI_BUILD = f"UI_BUILD_{time.strftime('%Y-%m-%d')}A"

runtime = build_runtime_state(ctx)

GRAPHICS_DIR = runtime.graphics_dir

GRAPHICS_LOGOS_DIR = runtime.graphics_logos_dir
GRAPHICS_BRAND_DIR = runtime.graphics_brand_dir
GRAPHICS_CLIENT_DIR = runtime.graphics_client_dir

CLUBAL_ICON_FILE = runtime.clubal_icon_file
CLIENT_LOGO_DIRNAME = runtime.client_logo_dirname
CLIENT_LOGO_FALLBACK = runtime.client_logo_fallback

LOGS_DIR = runtime.logs_dir
LOG_PATH = runtime.log_path
LOG_ARCHIVE_DIR = runtime.log_archive_dir

log = runtime.log

EXCEL_PATH = runtime.excel_path

class ClubalApp(tk.Tk):
    def __init__(self):
        self.ctx = ctx
        super().__init__()

        # DPI / Tk scaling: estabiliza o mesmo layout em 1360x768 e 1920x1080 (com escalas diferentes)
        force_tk_scaling_96dpi(self)

        self.title("CLUBAL - Club Agenda Live")
        self.attributes("-fullscreen", True)
        self.configure(bg="#f5f7fb")

        # Estado / caches
        self.is_day_theme = theme_is_day()
        self._apply_theme()

        self.all_items: List[ClassItem] = []
        self.last_excel_mtime: Optional[float] = None

        self.weather_last_fetch = 0.0
        self.weather_res: Optional[weather_mod.WeatherResult] = None
        self._weather_lock = threading.Lock()
        self._weather_inflight = False

        self._last_zero_agenda_log_ts = 0.0
        self._last_housekeeping_ts = 0.0

        self._last_layout_sig = None                 # (w,h,theme)
        self._last_header_geom = None                # (hours_w, weather_w, card_h, header_h)
        self._last_hours_minute_key = None           # evita updates desnecessários no hours
        self._last_agenda_run_ts = 0.0               # throttle agenda
        self._last_weather_ui_key = None             # evita redraw desnecessário do clima

        # Debug via variável de ambiente:
        # - CLUBAL_DEBUG_LAYOUT=1 (marca áreas na UI)
        # - CLUBAL_DEBUG_AGENDA=1  (logs detalhados da agenda)

        self.DEBUG_LAYOUT = str(os.environ.get("CLUBAL_DEBUG_LAYOUT", "0")).strip().lower() in ("1", "true", "yes", "on")
        self.DEBUG_AGENDA = str(os.environ.get("CLUBAL_DEBUG_AGENDA", "0")).strip().lower() in ("1", "true", "yes", "on")

        # Referências de UI criadas externamente por app.main_ui_builder.
        # Isso mantém o Pylance ciente dos atributos mesmo após a extração
        # do builder para fora da classe.
        self.header: Any = None
        self.header_bg: Any = None
        self.header_panel: Any = None
        self.header_panel_edge: Any = None
        self.header_panel_edge2: Any = None
        self.header_panel_edge3: Any = None
        self.header_panel_edge4: Any = None
        self.header_panel_top_glow: Any = None
        self.header_bottom_line: Any = None
        self.header_right: Any = None

        self.left_stack: Any = None
        self.logos_row: Any = None
        self.clubal_slot: Any = None
        self.logo_lbl: Any = None
        self.logo_img: Any = None

        self.client_slot: Any = None
        self.client_logo_lbl: Any = None
        self.client_logo_img: Any = None

        self.datecard: Any = None
        self.datecard_canvas: Any = None
        self._date_text_id: Any = None
        self._date_shadow_id: Any = None
        self._datecard_h: Any = None

        self.clockbox: Any = None
        self.clockcard: Any = None
        self.clock_inner: Any = None
        self.clock_center: Any = None
        self._clockcard_h: Any = None

        self.f_date_line: Any = None
        self.f_time_main: Any = None
        self.f_time_sec: Any = None

        self.header_onpanel_main: Any = None
        self.header_onpanel_soft: Any = None

        self.time_hhmm_lbl: Any = None
        self.time_ss_lbl: Any = None

        self.right_center: Any = None
        self.hours_card: Any = None
        self.weather_card: Any = None

        self.div: Any = None
        self.div_hi_line: Any = None
        self.div_lo_line: Any = None

        self.main: Any = None
        self.vdiv: Any = None
        self.agora: Any = None
        self.prox: Any = None

        self._right_vspacer_top: Any = None
        self._right_vspacer_bottom: Any = None

        self.bind("<Escape>", lambda e: self.destroy())

        rotate_logs_if_needed(LOG_PATH, LOG_ARCHIVE_DIR, logger=log)

        try:
            weather_mod.housekeeping(app_dir=str(self.ctx.paths.app_dir), logger=log)
        except Exception as e:
            log(f"[WEATHER] Housekeeping error {type(e).__name__}: {e}")

        # (opcional) prewarm leve dos ícones oficiais (background, não bloqueia UI)
        try:
            fn = getattr(weather_mod, "start_icon_pack_update_async", None)
            if callable(fn):
                fn(
                    app_dir=str(self.ctx.paths.app_dir),
                    logger=log,
                    user_agent="CLUBAL-AgendaLive/2.0 (contact: local)",
                )
        except Exception as e:
            log(f"[WEATHER] Icon prewarm start error {type(e).__name__}: {e}")

        self._build_ui()

        self.bind("<Configure>", self._on_root_configure)

        self._reload_excel_if_needed(force=True)
        self._tick()

        # ✅ antes: 9000 (9s). Agora mais confortável:
        self.after(MS_HOURS_ROTATE, self._rotate_hours)
    # -------------------------
    # Helpers
    # -------------------------
    def _blend_hex(self, a: str, b: str, t: float) -> str:
        """
        Mistura duas cores hex (#RRGGBB). t=0 -> a, t=1 -> b
        """
        try:
            a = (a or "#000000").strip()
            b = (b or "#000000").strip()
            if not a.startswith("#"):
                a = "#" + a
            if not b.startswith("#"):
                b = "#" + b

            t = float(t)
            if t < 0.0:
                t = 0.0
            if t > 1.0:
                t = 1.0

            ar = int(a[1:3], 16)
            ag = int(a[3:5], 16)
            ab = int(a[5:7], 16)

            br = int(b[1:3], 16)
            bg = int(b[3:5], 16)
            bb = int(b[5:7], 16)

            rr = int(ar + (br - ar) * t)
            rg = int(ag + (bg - ag) * t)
            rb = int(ab + (bb - ab) * t)

            return f"#{rr:02x}{rg:02x}{rb:02x}"
        except Exception:
            return a if a else "#000000"

    def _ui_tokens(self) -> dict:
        """
        Tokens centralizados de layout/visual.
        Futuramente pode virar um módulo separado (ex.: ui_tokens.py).
        """
        return {
            "sp_4": SP_4,
            "sp_8": SP_8,
            "sp_12": SP_12,
            "sp_16": SP_16,
            "sp_20": SP_20,
            "sp_24": SP_24,
            "sp_32": SP_32,
            "radius_sm": RADIUS_SM,
            "radius_md": RADIUS_MD,
            "radius_lg": RADIUS_LG,
            "shadow_soft": SHADOW_SOFT,
            "shadow_md": SHADOW_MD,
            "ms_card_rotate": MS_CARD_ROTATE,
            "ms_hours_rotate": MS_HOURS_ROTATE,
        }

    # -------------------------
    # Theme
    # -------------------------

    def _apply_theme(self):
        self.is_day_theme = theme_is_day()
        palette = build_app_palette(self.is_day_theme)

        self.bg_root = palette["bg_root"]
        self.bg_header = palette["bg_header"]
        self.fg_primary = palette["fg_primary"]
        self.fg_soft = palette["fg_soft"]
        self.div_main = palette["div_main"]
        self.div_hi = palette["div_hi"]
        self.div_lo = palette["div_lo"]

        self.configure(bg=self.bg_root)

    def _pil_contain_to_size(self, path: str, w: int, h: int):
        return pil_contain_to_size(path, w, h)

    def _refresh_logo(self):
        refresh_logo(
            self,
            graphics_brand_dir=GRAPHICS_BRAND_DIR,
            clubal_icon_file=CLUBAL_ICON_FILE,
            img_path_try=_img_path_try,
        )

    def _refresh_client_logo(self):
        refresh_client_logo(
            self,
            graphics_client_dir=GRAPHICS_CLIENT_DIR,
            first_image_in_dir=_first_image_in_dir,
        )

    def _build_datecard_candidates_ptbr(self) -> List[str]:
        return build_datecard_candidates_ptbr()

    def _ellipsis_to_fit(self, text: str, font_obj: tkfont.Font, max_w: int) -> str:
        if max_w <= 8:
            return "..."

        if font_obj.measure(text) <= max_w:
            return text

        ell = "..."
        if font_obj.measure(ell) > max_w:
            return ""

        # Tenta preservar começo útil
        lo = 0
        hi = len(text)
        best = ell

        while lo <= hi:
            mid = (lo + hi) // 2
            cand = text[:mid].rstrip() + ell
            if font_obj.measure(cand) <= max_w:
                best = cand
                lo = mid + 1
            else:
                hi = mid - 1

        return best

    def _update_datecard_text_adaptive(self):
        """
        Ajusta texto e fonte do DateCard ao espaço real disponível.
        Estratégia:
        1) tenta fonte alvo atual (definida no _layout_update)
        2) reduz fonte progressivamente
        3) testa versões cada vez mais curtas
        4) último caso: ellipsis coerente
        """
        try:
            if not hasattr(self, "datecard_canvas"):
                return
            if not hasattr(self, "f_date_line"):
                return
            if not hasattr(self, "_date_text_id") or self._date_text_id is None:
                return

            w = self.datecard_canvas.winfo_width()
            h = self.datecard_canvas.winfo_height()
            if w <= 20 or h <= 12:
                return

            # margem interna horizontal do DateCard
            max_w = max(40, w - 28)

            # chave para evitar updates desnecessários / flicker
            lt = time.localtime()
            key = (
                w,
                h,
                lt.tm_year,
                lt.tm_mon,
                lt.tm_mday,
                lt.tm_wday,
                getattr(self.f_date_line, "cget")("size"),
            )
            if getattr(self, "_date_fit_last_key", None) == key:
                return

            base_size = int(self.f_date_line.cget("size"))
            max_size = max(12, base_size)
            min_size = 11

            # fonte temporária para medir sem "pular" a fonte principal a cada teste
            test_font = tkfont.Font(
                family=self.f_date_line.cget("family"),
                size=max_size,
                weight=self.f_date_line.cget("weight")
            )

            candidates = self._build_datecard_candidates_ptbr()

            chosen_text = None
            chosen_size = max_size

            # tenta da fonte maior para menor (passos suaves)
            for sz in range(max_size, min_size - 1, -1):
                test_font.configure(size=sz)

                for cand in candidates:
                    if test_font.measure(cand) <= max_w:
                        chosen_text = cand
                        chosen_size = sz
                        break

                if chosen_text is not None:
                    break

            # último caso: ellipsis sobre a menor versão
            if chosen_text is None:
                test_font.configure(size=min_size)
                fallback = candidates[-1] if candidates else formal_date_line_ptbr()
                chosen_text = self._ellipsis_to_fit(fallback, test_font, max_w)
                chosen_size = min_size

            # aplica só se mudou de verdade
            apply_key = (chosen_text, chosen_size, w, h)
            if getattr(self, "_date_fit_last_apply", None) == apply_key:
                self._date_fit_last_key = key
                return

            # aplica na fonte real
            if int(self.f_date_line.cget("size")) != int(chosen_size):
                self.f_date_line.configure(size=int(chosen_size))

            self.datecard_canvas.itemconfig(self._date_text_id, text=chosen_text, font=self.f_date_line)
            if hasattr(self, "_date_shadow_id") and self._date_shadow_id is not None:
                self.datecard_canvas.itemconfig(self._date_shadow_id, text=chosen_text, font=self.f_date_line)

            self._date_fit_last_key = key
            self._date_fit_last_apply = apply_key

        except Exception:
            pass

    # -------------------------
    # Header sizing
    # -------------------------
    def _calc_header_geometry(self):
        sw = self.winfo_width()
        sh = self.winfo_height()

        if sw < 800:
            sw = max(1280, self.winfo_screenwidth())
        if sh < 600:
            sh = max(720, self.winfo_screenheight())

        hours_w, weather_w, card_h, header_h, _right_w = calc_header_geometry(sw, sh)
        return hours_w, weather_w, card_h, header_h

    def _build_ui(self):
        build_main_ui(self, logger=log)

    def _layout_update(self):
        try:
            hours_w, weather_w, card_h, header_h = self._calc_header_geometry()
            new_geom = (hours_w, weather_w, card_h, header_h)

            if new_geom != self._last_header_geom:
                self._last_header_geom = new_geom

                if hasattr(self, "header"):
                    self.header.configure(height=header_h)

                card_h_fill = card_h
                try:
                    hr_h = self.header_right.winfo_height()
                    if hr_h and hr_h > 10:
                        card_h_fill = int(hr_h - 24)
                        card_h_fill = max(190, min(card_h_fill, 360))
                except Exception:
                    card_h_fill = card_h

                if hasattr(self, "hours_card"):
                    self.hours_card.configure(width=hours_w, height=card_h_fill)
                if hasattr(self, "weather_card"):
                    self.weather_card.configure(width=weather_w, height=card_h_fill)

                if hasattr(self, "logo_lbl"):
                    self._refresh_logo()
                if hasattr(self, "client_logo_lbl"):
                    self._refresh_client_logo()

            # ✅ fontes + alturas (relógio + datecard)
            header_h_now = header_h
            try:
                if hasattr(self, "header"):
                    header_h_now = self.header.winfo_height() or header_h
            except Exception:
                header_h_now = header_h

            # alturas confortáveis e consistentes
            try:
                if hasattr(self, "datecard_canvas"):
                    self._datecard_h = int(max(52, min(78, header_h_now * 0.12)))
                    self.datecard_canvas.configure(height=self._datecard_h)
            except Exception:
                pass

            try:
                if hasattr(self, "clockcard"):
                    self._clockcard_h = int(max(92, min(150, header_h_now * 0.22)))
                    self.clockcard.configure(height=self._clockcard_h)
            except Exception:
                pass

            if hasattr(self, "f_time_main"):
                try:
                    main_sz = int(max(28, min(56, (header_h_now * 0.140) + 2)))
                    self.f_time_main.configure(size=main_sz)

                    if hasattr(self, "f_time_sec"):
                        sec_sz = int(max(14, min(26, main_sz * 0.48)))
                        self.f_time_sec.configure(size=sec_sz)

                    if hasattr(self, "f_date_line"):
                        line_sz = int(max(16, min(24, header_h_now * 0.070)))
                        self.f_date_line.configure(size=line_sz)

                    # ✅ Recalcula texto/fonte final do DateCard com base no espaço real
                    self._update_datecard_text_adaptive()

                except Exception:
                    pass

        except Exception:
            log("Layout update error:\n" + traceback.format_exc())

    def _on_root_configure(self, _evt=None):
        try:
            w = self.winfo_width()
            h = self.winfo_height()
            sig = (w, h, self.is_day_theme)
            if sig == self._last_layout_sig:
                return
            self._last_layout_sig = sig
            self._layout_update()
        except Exception:
            pass

    # -------------------------
    # Hours rotate
    # -------------------------
    def _rotate_hours(self):
        try:
            self.hours_card.tick_rotate()
        finally:
            # Rotação do HoursCard (ms).
            self.after(16000, self._rotate_hours)

    # -------------------------
    # Excel reload
    # -------------------------
    def _reload_excel_if_needed(self, force: bool = False):
        self.all_items, self.last_excel_mtime = reload_excel_if_needed(
            EXCEL_PATH,
            self.all_items,
            self.last_excel_mtime,
            force=force,
            logger=log,
        )

    # -------------------------
    # Agenda compute
    # -------------------------
    def _compute_now_next(self) -> Tuple[List[Tuple], List[Tuple]]:
        now_dt = datetime.now()

        now_cards, next_cards, window_end, discard_day, discard_time, discard_other = compute_now_next_cards(
            now_dt=now_dt,
            all_items=self.all_items,
            window_minutes=120,
            log_fn=log,
        )

        if self.all_items and (len(now_cards) == 0 and len(next_cards) == 0):
            if time.time() - self._last_zero_agenda_log_ts > 60:
                self._last_zero_agenda_log_ts = time.time()
                sample = self.all_items[:4]
                log(
                    "[AGENDA] 0 em AGORA/PRÓXIMAS | "
                    f"now={now_dt.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"window_end={window_end.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"today_code={today_3letters_noaccent()} "
                    f"discard_day={discard_day} "
                    f"discard_time={discard_time} "
                    f"discard_other={discard_other} "
                    f"sample_items={sample}"
                )

        return now_cards, next_cards

    # -------------------------
    # Main tick
    # -------------------------
    def _tick(self):
        try:
            new_theme = theme_is_day()

            handle_theme_rebuild_if_needed(
                self,
                new_theme_is_day=new_theme,
            )

            _d, t, _wd = date_time_strings()

            refresh_header_clock_and_hours(
                self,
                time_text=t,
            )

            self._reload_excel_if_needed(force=False)

            refresh_agenda_if_due(
                self,
                min_interval_sec=15,
            )

            tick_weather_refresh(
                self,
                app_dir=str(self.ctx.paths.app_dir),
                logger=log,
            )

            apply_weather_result_if_changed(
                self,
                city_label="Alfenas",
            )

            tick_housekeeping_if_due(
                self,
                log_path=LOG_PATH,
                log_archive_dir=LOG_ARCHIVE_DIR,
                app_dir=str(self.ctx.paths.app_dir),
                logger=log,
                min_interval_sec=86400,
            )

        except Exception:
            log("Tick error:\n" + traceback.format_exc())

        self.after(1000, self._tick)

if __name__ == "__main__":
    try:
        enable_windows_dpi_awareness()  # precisa ocorrer antes do Tk criar janelas
        selftest_geometry(logger=log)
        ClubalApp().mainloop()
    except Exception:
        log("Fatal error:\n" + traceback.format_exc())