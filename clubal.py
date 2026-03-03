
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

ctx = bootstrap()

from infra.xlsx_loader import reload_classes_if_needed

import weather_service as weather_mod

from datetime import datetime, timedelta, date as dt_date, time as dt_time

# Build ID para diagnóstico (logs).
CLUBAL_UI_BUILD = f"UI_BUILD_{time.strftime('%Y-%m-%d')}A"

# -------------------------
# Infra/IO consolidado em bootstrap + ctx.paths + logging local
# -------------------------

GRAPHICS_DIR = str(ctx.paths.assets_dir)

# -------------------------
# Graphics: fixed CLUBAL icon + dynamic client logo folder
# -------------------------

GRAPHICS_LOGOS_DIR = os.path.join(GRAPHICS_DIR, "logos")
GRAPHICS_BRAND_DIR = os.path.join(GRAPHICS_LOGOS_DIR, "brand")
GRAPHICS_CLIENT_DIR = os.path.join(GRAPHICS_LOGOS_DIR, "client")

CLUBAL_ICON_FILE = "CLUBAL_ICO.png"   # dentro de graphics/logos/brand/
CLIENT_LOGO_DIRNAME = os.path.join("logos", "client")
CLIENT_LOGO_FALLBACK = "logo_sesi_default.png"
configure_image_search_dirs([
    GRAPHICS_DIR,
    GRAPHICS_LOGOS_DIR,
    GRAPHICS_BRAND_DIR,
    GRAPHICS_CLIENT_DIR,
    os.path.join(GRAPHICS_DIR, "weather", "icons"),
    os.path.join(GRAPHICS_DIR, "weather", "bg"),
])

# logs em local gravável (ou desabilitados, se o ambiente bloquear escrita)
LOGS_DIR = str(ctx.paths.logs_dir) if ctx.paths.logs_dir is not None else None
LOG_PATH = os.path.join(LOGS_DIR, "clubal.log") if LOGS_DIR else None
LOG_ARCHIVE_DIR = os.path.join(LOGS_DIR, "archive") if LOGS_DIR else None

# Rotação/limpeza de logs (evita crescimento infinito de arquivo).
LOG_ROTATE_MAX_BYTES = 2 * 1024 * 1024   # 2MB
LOG_ARCHIVE_KEEP = 6                     # mantém os últimos N logs arquivados
LOG_ARCHIVE_MAX_AGE_DAYS = 30            # e/ou apaga logs muito antigos

def log(msg: str) -> None:
    try:
        rotate_logs_if_needed(LOG_PATH, LOG_ARCHIVE_DIR)
        write_log(LOG_PATH, LOGS_DIR, msg)
    except Exception:
        pass


def _ensure_log_archive_dir() -> bool:
    if not LOG_ARCHIVE_DIR:
        return False
    try:
        os.makedirs(LOG_ARCHIVE_DIR, exist_ok=True)
        return True
    except Exception:
        return False

def _selftest_geometry(logger=log) -> None:
    """
    Teste rápido (sem UI) dos cálculos de geometria em resoluções comuns.
    Ative com: CLUBAL_SELFTEST=1
    """
    try:
        if str(os.environ.get("CLUBAL_SELFTEST", "0")).strip() not in ("1", "TRUE", "YES", "ON"):
            return

        tests = [
            (1360, 768),
            (1920, 1080),
            (2560, 1440),
            (3840, 2160),
        ]

        logger("[SELFTEST] Geometry test start")

        for sw, sh in tests:
            hours_w, weather_w, card_h, header_h, right_w = calc_header_geometry(sw, sh)

            ok1 = card_h <= (header_h - 16)
            ok2 = right_w <= sw

            logger(
                "[SELFTEST] "
                f"{sw}x{sh} -> hours_w={hours_w} weather_w={weather_w} card_h={card_h} header_h={header_h} right_w={right_w} "
                f"ok_card_in_header={ok1} ok_right_fits_screen={ok2}"
            )

        logger("[SELFTEST] Geometry test end")
    except Exception as e:
        try:
            logger(f"[SELFTEST] Exception {type(e).__name__}: {e}")
        except Exception:
            pass

# -------------------------
# Excel path (loader lives in infra.xlsx_loader)
# -------------------------
EXCEL_PATH = os.path.join(str(ctx.paths.data_dir), "grade.xlsx")

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

        # ✅ antes: 9000 (9s). Agora mais confortável/premium:
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

    # -------------------------
    # Logo (CLUBAL) - slot fixo
    # -------------------------
    def _pil_contain_to_size(self, path: str, w: int, h: int):
        """
        Resize tipo 'CONTAIN' (encaixa sem cortar), centralizado, mantendo transparência.
        Retorna PhotoImage (PIL).
        """
        im = _pil_open_rgba(path)
        iw, ih = im.size
        if iw <= 0 or ih <= 0:
            return None

        scale = min(w / iw, h / ih)
        nw = max(1, int(iw * scale))
        nh = max(1, int(ih * scale))
        im = im.resize((nw, nh), PIL_LANCZOS)

        canvas = _pil_new_rgba((w, h), (0, 0, 0, 0))
        x = (w - nw) // 2
        y = (h - nh) // 2
        canvas.paste(im, (x, y), im)

        return _pil_photo_image(canvas)

    def _refresh_logo(self):
        """
        Logo do CLUBAL (fixo):
        Sempre usa graphics/logos/brand/CLUBAL_ICO.png
        """
        p = os.path.join(GRAPHICS_BRAND_DIR, CLUBAL_ICON_FILE)
        if not os.path.exists(p):
            # fallback (tenta achar por busca)
            p = _img_path_try("CLUBAL_ICO") or _img_path_try(CLUBAL_ICON_FILE)

        if not p or not os.path.exists(p):
            if hasattr(self, "logo_lbl"):
                self.logo_lbl.configure(image="")
            return

        try:
            target_w = 150
            target_h = 150

            if hasattr(self, "clubal_slot") and self.clubal_slot.winfo_exists():
                self.clubal_slot.update_idletasks()
                sw = self.clubal_slot.winfo_width()
                sh = self.clubal_slot.winfo_height()
                if sw and sw > 10:
                    target_w = max(90, sw - 10)
                if sh and sh > 10:
                    target_h = max(90, sh - 10)

            img = None

            if PIL_OK:
                try:
                    img = self._pil_contain_to_size(p, target_w, target_h)
                except Exception:
                    img = None

            if img is None:
                tkimg = tk.PhotoImage(file=p)
                fx = max(1, (tkimg.width() + target_w - 1) // target_w) if tkimg.width() > target_w else 1
                fy = max(1, (tkimg.height() + target_h - 1) // target_h) if tkimg.height() > target_h else 1
                f = max(fx, fy)
                if f > 1:
                    tkimg = tkimg.subsample(f)
                img = tkimg

            self.logo_img = img
            self.logo_lbl.configure(image=self.logo_img)

        except Exception:
            if hasattr(self, "logo_lbl"):
                self.logo_lbl.configure(image="")

    def _refresh_client_logo(self):
        """
        Logo do CLIENTE (dinâmico):
        Usa a PRIMEIRA imagem (por nome) dentro de graphics/logos/client/
        """
        try:
            client_dir = GRAPHICS_CLIENT_DIR
            p = _first_image_in_dir(client_dir)

            if not p:
                if hasattr(self, "client_logo_lbl"):
                    self.client_logo_lbl.configure(image="")
                return

            target_w = 320
            target_h = 150

            if hasattr(self, "client_slot") and self.client_slot.winfo_exists():
                self.client_slot.update_idletasks()
                sw = self.client_slot.winfo_width()
                sh = self.client_slot.winfo_height()
                if sw and sw > 10:
                    target_w = max(160, sw - 10)
                if sh and sh > 10:
                    target_h = max(90, sh - 10)

            img = None

            if PIL_OK:
                try:
                    img = self._pil_contain_to_size(p, target_w, target_h)
                except Exception:
                    img = None

            if img is None:
                tkimg = tk.PhotoImage(file=p)
                fx = max(1, (tkimg.width() + target_w - 1) // target_w) if tkimg.width() > target_w else 1
                fy = max(1, (tkimg.height() + target_h - 1) // target_h) if tkimg.height() > target_h else 1
                f = max(fx, fy)
                if f > 1:
                    tkimg = tkimg.subsample(f)
                img = tkimg

            self.client_logo_img = img
            self.client_logo_lbl.configure(image=self.client_logo_img)
            self.client_logo_lbl.place(relx=0.5, rely=0.5, anchor="center")

        except Exception:
            if hasattr(self, "client_logo_lbl"):
                self.client_logo_lbl.configure(image="")

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

    # -------------------------
    # Build UI (ÚNICO)
    # -------------------------
    def _build_ui(self):

        # ✅ cleanup explícito (evita after() pendurado em rebuild de tema)
        try:
            if hasattr(self, "agora") and self.agora is not None:
                try:
                    self.agora.dispose()
                except Exception:
                    pass
            if hasattr(self, "hours_card") and self.hours_card is not None:
                try:
                    self.hours_card.dispose()
                except Exception:
                    pass
            if hasattr(self, "prox") and self.prox is not None:
                try:
                    self.prox.dispose()
                except Exception:
                    pass
            if hasattr(self, "weather_card") and self.weather_card is not None:
                try:
                    self.weather_card.dispose()
                except Exception:
                    pass
        except Exception:
            pass

        for w in list(self.winfo_children()):
            try:
                w.destroy()
            except Exception:
                pass

        hours_w, weather_w, card_h, header_h = self._calc_header_geometry()
        right_w = int(hours_w + 40 + weather_w) + 24
        self._last_header_geom = (hours_w, weather_w, card_h, header_h)

        self.header = tk.Frame(self, bg=self.bg_header, height=header_h)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        # -------------------------
        # Header background (B)
        # -------------------------
        if self.is_day_theme:
            header_base = self.bg_header
            panel_fill = "#0b2b5e"
            panel_bottom = "#0a254e"
            panel_edge = "#0f3a77"
            inset = SP_12
        else:
            header_base = "#050e1a"
            panel_fill = "#0a1f38"
            panel_bottom = "#08182c"
            panel_edge = "#123d73"
            inset = SP_16

        self.header_bg = tk.Frame(self.header, bg=header_base)
        self.header_bg.place(x=0, y=0, relwidth=1, relheight=1)

        self.header_panel = tk.Frame(self.header, bg=panel_fill)
        self.header_panel.place(x=inset, y=inset, relwidth=1, width=-(2 * inset), relheight=1, height=-(2 * inset))

        self.header_panel_edge = tk.Frame(self.header_panel, bg=panel_edge)
        self.header_panel_top_glow = tk.Frame(self.header_panel, bg="#1b4f91", height=1)
        self.header_panel_top_glow.place(x=0, y=1, relwidth=1)
        self.header_panel_edge.place(x=0, y=0, relwidth=1, height=1)

        self.header_panel_edge2 = tk.Frame(self.header_panel, bg=panel_edge)
        self.header_panel_edge2.place(x=0, y=0, width=1, relheight=1)

        self.header_panel_edge3 = tk.Frame(self.header_panel, bg=panel_edge)
        self.header_panel_edge3.place(relx=1.0, x=-1, y=0, width=1, relheight=1)

        self.header_panel_edge4 = tk.Frame(self.header_panel, bg=panel_edge)
        self.header_panel_edge4.place(x=0, rely=1.0, y=-1, relwidth=1, height=1)

        self.header_bottom_line = tk.Frame(self.header_panel, bg=panel_bottom, height=3)
        self.header_bottom_line.pack(side="bottom", fill="x")

        self.header_bg.lower()
        self.header_panel.lower()

        header_fill = panel_fill

        # HEADER GRID (2 linhas)
        self.header.grid_rowconfigure(0, weight=1)
        self.header.grid_rowconfigure(1, weight=1)

        self.header.grid_columnconfigure(0, weight=1)
        self.header.grid_columnconfigure(1, weight=0, minsize=right_w)

        # LEFT STACK
        self.left_stack = tk.Frame(self.header, bg=header_fill)
        self.left_stack.grid(
            row=0,
            column=0,
            rowspan=2,
            sticky="nsew",
            padx=(SP_12, SP_8),
            pady=(SP_8, SP_12)
        )
        self.left_stack.grid_columnconfigure(0, weight=1)
        self.left_stack.grid_rowconfigure(0, weight=0)
        self.left_stack.grid_rowconfigure(1, weight=0)
        self.left_stack.grid_rowconfigure(2, weight=1)

        # Row 0: logos
        LOGOS_ROW_H = 150
        CLUBAL_SLOT_S = LOGOS_ROW_H

        self.logos_row = tk.Frame(self.left_stack, bg=header_fill, height=LOGOS_ROW_H)
        self.logos_row.grid(row=0, column=0, sticky="ew")
        self.logos_row.grid_propagate(False)

        self.logos_row.grid_columnconfigure(0, weight=0, minsize=CLUBAL_SLOT_S)
        self.logos_row.grid_columnconfigure(1, weight=1, minsize=160)

        self.clubal_slot = tk.Frame(self.logos_row, bg=header_fill, width=CLUBAL_SLOT_S, height=LOGOS_ROW_H)
        self.clubal_slot.grid(row=0, column=0, sticky="w")
        self.clubal_slot.grid_propagate(False)

        self.logo_img = None
        self.logo_lbl = tk.Label(self.clubal_slot, bg=header_fill)
        self.logo_lbl.place(relx=0.5, rely=0.5, anchor="center")

        self.client_slot = tk.Frame(self.logos_row, bg=header_fill, height=LOGOS_ROW_H)
        self.client_slot.grid(row=0, column=1, sticky="ew", padx=(18, 0))
        self.client_slot.grid_propagate(False)

        self.client_logo_img = None
        self.client_logo_lbl = tk.Label(self.client_slot, bg=header_fill)
        self.client_logo_lbl.place(relx=0.5, rely=0.5, anchor="center")

        if self.DEBUG_LAYOUT:
            self.clubal_slot.configure(highlightthickness=2, highlightbackground="#00ff00")
            self.client_slot.configure(highlightthickness=2, highlightbackground="#00ffff")

        self._refresh_logo()
        self._refresh_client_logo()

        # Row 1: DateCard
        self.datecard = tk.Frame(self.left_stack, bg=header_fill)
        self.datecard.grid(row=1, column=0, sticky="ew", pady=(10, 8))

        if self.DEBUG_LAYOUT:
            self.datecard.configure(highlightthickness=2, highlightbackground="#ffd000")

        # ✅ altura do datecard dinâmica (refinada no _layout_update)
        self._datecard_h = 58

        # ✅ DateCard: “glass” com relevo VISÍVEL (texto desenhado no canvas, sem Label por cima)
        if self.is_day_theme:
            datecard_bg = self._blend_hex(panel_fill, "#ffffff", 0.10)
            datecard_border = self._blend_hex(panel_fill, "#ffffff", 0.20)
            datecard_fg = "#ffffff"
            shadow_stipple = "gray12"
        else:
            datecard_bg = self._blend_hex("#0b223c", "#ffffff", 0.06)
            datecard_border = self._blend_hex("#132744", "#ffffff", 0.08)
            datecard_fg = "#eaf2ff"
            shadow_stipple = "gray12"

        self.datecard_canvas = RoundedFrame(
            self.datecard,
            radius=RADIUS_SM,
            bg=datecard_bg,
            border=datecard_border,
            shadow=True,
            shadow_offset=(2, 3),
            shadow_stipple=shadow_stipple,
            gloss=True,
            gloss_inset=3,
            height=self._datecard_h
        )
        self.datecard_canvas.pack(fill="x", expand=False)
        self.datecard_canvas.pack_propagate(False)

        self.f_date_line = tkfont.Font(
            family="Segoe UI",
            size=18,
            weight="bold"
        )

        # DateCard: texto desenhado no Canvas para controle fino de layout (sem Label por cima).
        self._date_text_id = None
        self._date_shadow_id = None

        def _draw_date_text(_evt=None):
            try:
                w = self.datecard_canvas.winfo_width()
                h = self.datecard_canvas.winfo_height()
                if w <= 10 or h <= 10:
                    return

                if self._date_text_id is None:
                    self._date_shadow_id = self.datecard_canvas.create_text(
                        (w // 2) + 1, (h // 2) + 1,
                        anchor="center",
                        text="",
                        fill="#061a33" if self.is_day_theme else "#000000",
                        font=self.f_date_line
                    )
                    self._date_text_id = self.datecard_canvas.create_text(
                        w // 2, h // 2,
                        anchor="center",
                        text="",
                        fill=datecard_fg,
                        font=self.f_date_line
                    )
                else:
                    shadow_id = self._date_shadow_id
                    text_id = self._date_text_id

                    if shadow_id is not None:
                        self.datecard_canvas.coords(shadow_id, (w // 2) + 1, (h // 2) + 1)
                    if text_id is not None:
                        self.datecard_canvas.coords(text_id, w // 2, h // 2)

            except Exception:
                pass

        self.datecard_canvas.bind("<Configure>", _draw_date_text)
        self.after(0, _draw_date_text)

        # Row 2: Relógio (agora com “glass” próprio para garantir contraste e conforto)
        self.clockbox = tk.Frame(self.left_stack, bg=header_fill)
        self.clockbox.grid(row=2, column=0, sticky="nsew")

        if self.DEBUG_LAYOUT:
            self.clockbox.configure(highlightthickness=2, highlightbackground="#ff0000")

        mono_family = "Cascadia Mono"
        try:
            self.f_time_main = tkfont.Font(family=mono_family, size=34, weight="bold")
        except Exception:
            self.f_time_main = tkfont.Font(family="Consolas", size=34, weight="bold")

        try:
            self.f_time_sec = tkfont.Font(family=mono_family, size=22, weight="bold")
        except Exception:
            self.f_time_sec = tkfont.Font(family="Consolas", size=22, weight="bold")

        # Contraste do texto no painel do header (relógio)
        if self.is_day_theme:
            self.header_onpanel_main = "#ffffff"
            self.header_onpanel_soft = "#bcd3ff"
        else:
            self.header_onpanel_main = "#eaf2ff"
            self.header_onpanel_soft = "#b9c7dd"

        # ✅ clock “glass” (sem depender do fundo do header)
        if self.is_day_theme:
            clock_bg = self._blend_hex(panel_fill, "#ffffff", 0.08)
            clock_border = self._blend_hex(panel_fill, "#ffffff", 0.14)
            clock_shadow_stipple = "gray12"
        else:
            clock_bg = self._blend_hex("#0b223c", "#ffffff", 0.05)
            clock_border = self._blend_hex("#132744", "#ffffff", 0.08)
            clock_shadow_stipple = "gray12"

        self._clockcard_h = 110

        self.clockcard = RoundedFrame(
            self.clockbox,
            radius=RADIUS_MD,
            bg=clock_bg,
            border=clock_border,
            shadow=True,
            shadow_offset=SHADOW_SOFT,
            shadow_stipple=clock_shadow_stipple,
            gloss=True,
            gloss_inset=3,
            height=self._clockcard_h
        )
        self.clockcard.pack(fill="x", pady=(0, 0))
        self.clockcard.pack_propagate(False)

        self.clock_inner = tk.Frame(self.clockcard, bg=clock_bg)
        self.clock_inner.place(relx=0.5, rely=0.5, anchor="center")

        self.clock_center = tk.Frame(self.clock_inner, bg=clock_bg)
        self.clock_center.pack(anchor="center")

        self.time_hhmm_lbl = tk.Label(
            self.clock_center,
            text="00:00",
            font=self.f_time_main,
            fg=self.header_onpanel_main,
            bg=clock_bg,
            anchor="center"
        )
        self.time_hhmm_lbl.pack(side="left")

        self.time_ss_lbl = tk.Label(
            self.clock_center,
            text=":00",
            font=self.f_time_sec,
            fg=self.header_onpanel_soft,
            bg=clock_bg,
            anchor="center"
        )
        self.time_ss_lbl.pack(side="left", padx=(4, 0))

        if self.DEBUG_LAYOUT:
            self.clockcard.configure(highlightthickness=2, highlightbackground="#ff66ff")

        # RIGHT (hours + spacer + weather)
        self.header_right = tk.Frame(self.header, bg=header_fill, width=right_w)
        self.header_right.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="nsew",
            padx=SP_12,
            pady=(SP_8, SP_12)
        )
        self.header_right.lift()
        self.header_right.grid_propagate(False)

        self.header_right.grid_columnconfigure(0, weight=1)
        self.header_right.grid_rowconfigure(0, weight=1)
        self.header_right.grid_rowconfigure(1, weight=0)
        self.header_right.grid_rowconfigure(2, weight=1)

        self._right_vspacer_top = tk.Frame(self.header_right, bg=header_fill)
        self._right_vspacer_top.grid(row=0, column=0, sticky="nsew")

        self.right_center = tk.Frame(self.header_right, bg=header_fill)
        self.right_center.grid(row=1, column=0, sticky="nsew", padx=(0, 12))

        self._right_vspacer_bottom = tk.Frame(self.header_right, bg=header_fill)
        self._right_vspacer_bottom.grid(row=2, column=0, sticky="nsew")

        self.right_center.grid_rowconfigure(0, weight=1)
        self.right_center.grid_columnconfigure(0, weight=0)
        self.right_center.grid_columnconfigure(1, weight=0)
        self.right_center.grid_columnconfigure(2, weight=0)

        self.hours_card = HoursCard(
            self.right_center,
            is_day_theme=self.is_day_theme,
            rounded_frame_cls=RoundedFrame,
        )
        self.weather_card = WeatherCard(
            self.right_center,
            is_day_theme=self.is_day_theme,
            ctx=ctx,
            logger=log,
        )

        self.hours_card.grid(row=0, column=0, sticky="nsew")
        spacer = tk.Frame(self.right_center, bg=header_fill, width=40)
        spacer.grid(row=0, column=1, sticky="nsew")
        self.weather_card.grid(row=0, column=2, sticky="nsew", pady=6)

        self.hours_card.configure(width=hours_w, height=card_h)
        self.weather_card.configure(width=weather_w, height=card_h)

        self.hours_card.pack_propagate(False)
        self.weather_card.pack_propagate(False)

        if self.DEBUG_LAYOUT:
            self.header_right.configure(highlightthickness=2, highlightbackground="#ff00ff")

        # divider
        self.div = tk.Frame(self, bg=self.bg_root, height=3)
        self.div.pack(fill="x")

        self.div_hi_line = tk.Frame(self.div, bg=self.div_hi, height=1)
        self.div_hi_line.pack(fill="x", side="top")
        self.div_lo_line = tk.Frame(self.div, bg=self.div_lo, height=2)
        self.div_lo_line.pack(fill="x", side="top")

        # main
        self.main = tk.Frame(self, bg=self.bg_root)
        self.main.pack(fill="both", expand=True)

        self.main.grid_columnconfigure(0, weight=1, uniform="main")
        self.main.grid_columnconfigure(1, weight=0)
        self.main.grid_columnconfigure(2, weight=1, uniform="main")
        self.main.grid_rowconfigure(0, weight=1)

        self.vdiv = tk.Frame(self.main, bg="#1b3a5f", width=3)
        self.vdiv.grid(row=0, column=1, sticky="ns", padx=6, pady=14)

        self.agora = SectionFrame(
            self.main,
            "AGORA",
            is_day_theme=self.is_day_theme,
            rounded_frame_cls=RoundedFrame,
            card_cls=ClassCard,
        )
        self.prox = SectionFrame(
            self.main,
            "PRÓXIMAS",
            is_day_theme=self.is_day_theme,
            rounded_frame_cls=RoundedFrame,
            card_cls=ClassCard,
        )

        self.agora.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=(10, 14))
        self.prox.grid(row=0, column=2, sticky="nsew", padx=(8, 16), pady=(10, 14))

        self.after(0, self._layout_update)

    # -------------------------
    # Layout update (resize-safe)
    # -------------------------

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
        self.all_items, self.last_excel_mtime, _changed = reload_classes_if_needed(
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
        window_end = now_dt + timedelta(minutes=120)

        now_list, next_list, discard_day, discard_time, discard_other = agenda_compute_now_next(
            now_dt=now_dt,
            all_items=self.all_items,
            window_minutes=120,
            log_fn=log,
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
    # Weather async
    # -------------------------
    def _weather_worker(self):
        try:
            res = weather_mod.get_weather(
                city_label="Alfenas",
                lat=-21.4267,
                lon=-45.9470,
                app_dir=str(self.ctx.paths.app_dir),
                user_agent="CLUBAL-AgendaLive/2.0 (contact: local)",
                logger=log,
            )
            with self._weather_lock:
                self.weather_res = res
                self.weather_last_fetch = time.time()
        except Exception as e:
            log(f"[WEATHER] Worker error {type(e).__name__}: {e}")
        finally:
            with self._weather_lock:
                self._weather_inflight = False

    def _tick_weather(self):
        if (time.time() - self.weather_last_fetch) < 600 and self.weather_res is not None:
            return

        with self._weather_lock:
            if self._weather_inflight:
                return
            self._weather_inflight = True

        th = threading.Thread(target=self._weather_worker, daemon=True)
        th.start()

    def _tick_housekeeping(self):
        if time.time() - self._last_housekeeping_ts < 86400:
            return
        self._last_housekeeping_ts = time.time()
        try:
            rotate_logs_if_needed(LOG_PATH, LOG_ARCHIVE_DIR, logger=log)
            weather_mod.housekeeping(app_dir=str(self.ctx.paths.app_dir), logger=log)
        except Exception as e:
            log(f"[HK] error {type(e).__name__}: {e}")

    # -------------------------
    # Main tick
    # -------------------------
    def _tick(self):
        try:
            new_theme = theme_is_day()
            if new_theme != self.is_day_theme:
                self._apply_theme()
                self._build_ui()
                self._reload_excel_if_needed(force=True)
                self._last_weather_ui_key = None
                self._last_agenda_run_ts = 0.0
                self._last_hours_minute_key = None

            _d, t, _wd = date_time_strings()

            # DateCard (texto no Canvas) - adaptativo ao espaço real
            self._update_datecard_text_adaptive()

            # Relógio (HH:MM + :SS)
            hhmm, ss = split_clock_hhmm_ss(t)
            if hasattr(self, "time_hhmm_lbl"):
                self.time_hhmm_lbl.configure(text=hhmm)
            if hasattr(self, "time_ss_lbl"):
                self.time_ss_lbl.configure(text=f":{ss}")

            # HoursCard: só recalcula quando muda o minuto
            now = time.localtime()
            minute_key = (now.tm_wday, now.tm_hour, now.tm_min, getattr(self.hours_card, "_mode", 0))
            if minute_key != self._last_hours_minute_key:
                self._last_hours_minute_key = minute_key
                self.hours_card.update_view(force=False)

            # Excel
            self._reload_excel_if_needed(force=False)

            # Agenda: no máximo a cada 15s
            if time.time() - self._last_agenda_run_ts >= 15:
                self._last_agenda_run_ts = time.time()
                now_cards, next_cards = self._compute_now_next()
                self.agora.update_cards(now_cards)
                self.prox.update_cards(next_cards)

            # Weather fetch
            self._tick_weather()

            # Weather UI: só quando mudou
            with self._weather_lock:
                res = self.weather_res
            if res:
                key = (
                    getattr(res, "ok", None),
                    getattr(res, "source", None),
                    getattr(res, "temp_c", None),
                    getattr(res, "symbol_code", None),
                    getattr(res, "today_label", None),
                    getattr(res, "tomorrow_label", None),
                    getattr(res, "cache_ts", None),
                )
                if key != self._last_weather_ui_key:
                    self._last_weather_ui_key = key
                    self.weather_card.set_weather("Alfenas", res)

            self._tick_housekeeping()

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