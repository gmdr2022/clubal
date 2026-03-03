
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

ctx = bootstrap()

from infra.xlsx_loader import reload_classes_if_needed

import weather_service as weather_mod

from datetime import datetime, timedelta, date as dt_date, time as dt_time

# -------------------------
# DPI / Scaling (Windows) — estabiliza layout entre PCs (100%/125%/150%)
# -------------------------

def _enable_windows_dpi_awareness() -> None:
    """
    Torna o processo DPI-aware para evitar variações de escala entre máquinas.
    Deve rodar ANTES de criar qualquer janela Tk (antes de ClubalApp()).
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes  # noqa
        try:
            # Windows 10 (1607+) — melhor opção: Per-Monitor V2
            DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4  # constante (HANDLE)
            ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
            return
        except Exception:
            pass

        try:
            # Windows 8.1+ fallback
            PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
            return
        except Exception:
            pass

        try:
            # Windows Vista+ fallback
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    except Exception:
        pass

def _force_tk_scaling_96dpi(root: tk.Tk) -> float:
    """
    Força (ou não) a escala do Tk.

    Modo padrão (sem variável): FIXED_96DPI (o que você já usa hoje).
    Você pode mudar sem editar código usando variável de ambiente:

      CLUBAL_TK_SCALING=FIXED_96DPI   -> força 96dpi (96/72=1.3333)  [PADRÃO]
      CLUBAL_TK_SCALING=AUTO          -> não força nada (deixa Windows/Tk decidirem)
      CLUBAL_TK_SCALING=<float>       -> ex: 1.25 / 1.3333 / 1.5

    Retorna a escala aplicada (ou 0.0 se não aplicou).
    """
    try:
        mode = str(os.environ.get("CLUBAL_TK_SCALING", "FIXED_96DPI")).strip().upper().strip().upper()

        # AUTO: não mexe no scaling
        if mode in ("AUTO", "DEFAULT", "SYSTEM", "NONE"):
            return 0.0

        # FIXED_96DPI: comportamento atual
        if mode in ("FIXED_96DPI", "96DPI", "FIXED"):
            fixed = 96.0 / 72.0  # 1.333333...
            root.tk.call("tk", "scaling", fixed)
            return float(fixed)

        # número direto (ex.: 1.25 / 1.5)
        try:
            val = float(mode.replace(",", "."))
            if 0.8 <= val <= 3.0:
                root.tk.call("tk", "scaling", val)
                return float(val)
        except Exception:
            pass

        # fallback: mantém o atual
        return 0.0
    except Exception:
        return 0.0

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

# -------------------------
# Weather icon mapping
# -------------------------

def map_symbol_to_icon(symbol_code: Optional[str]) -> str:
    if not symbol_code:
        return "clouds"

    s = symbol_code.lower()
    if "thunder" in s:
        return "storm"
    if "snow" in s:
        return "snowflake"
    if "rain" in s or "sleet" in s:
        return "rainy-day"
    if "partlycloudy" in s:
        return "cloudy"
    if "cloudy" in s:
        return "clouds"
    if "clearsky" in s or "fair" in s:
        return "sun"
    return "clouds"

class WeatherCard(tk.Frame):
    """
    Card do clima (UI).

    Layout topo (novo):
    - Esquerda: "CLIMA ALFENAS" alinhado à esquerda do bloco.
    - Direita: status ao vivo (ex.: "CHUVA") alinhado à direita (cresce pra esquerda).
    - Se status não couber: vira letreiro rolando para a esquerda (clip real).
    - Status em CAIXA ALTA.

    Demais:
    - Ícone com mais destaque (sem linha/sep embaixo).
    - "TEMP. AGORA" vira dinâmico: online -> TEMP. AGORA | cache/offline -> CACHE HH:MM / OFFLINE
    - Robustez ícones (mantém último oficial válido).
    """

    def __init__(self, master, is_day_theme: bool):
        super().__init__(master, bd=0, highlightthickness=0)
        self.is_day_theme = is_day_theme
        self.ctx = globals().get("ctx", None)

        try:
            self.configure(bg=master["bg"])
        except Exception:
            pass

        # Base / frame
        self.base_bg = "#0b2b5e"
        self.border = "#081a38"
        self.line_soft = "#2b63b0" if is_day_theme else "#244a86"

        # Glass
        self.glass_fill = "#0a2a55" if is_day_theme else "#071a33"
        self.glass_edge = "#0f3a77" if is_day_theme else "#0b2a55"
        self.glass_high = "#1d5aa7" if is_day_theme else "#123d73"
        self.glass_low = "#061a33" if is_day_theme else "#041326"

        # Forecast strip: “glass” mais discreto
        if self.is_day_theme:
            self._forecast_strip_bg = self._blend_hex(self.glass_fill, "#ffffff", 0.14)
            self._forecast_strip_edge = self._blend_hex(self.glass_edge, "#ffffff", 0.10)
        else:
            self._forecast_strip_bg = self._blend_hex(self.glass_fill, "#ffffff", 0.08)
            self._forecast_strip_edge = self._blend_hex(self.glass_edge, "#ffffff", 0.06)

        # -------------------------
        # Glass transparency (PIL overlay)
        # -------------------------
        self._glass_alpha = 75 if is_day_theme else 90
        self._glass_img_cache: Dict[Tuple[int, int, int], object] = {}
        self._glass_img_refs: List[object] = []

        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0, bg=self.base_bg, relief="flat")
        self.canvas.pack(fill="both", expand=True)

        # Fonts (topo: "CLIMA" menor + cidade maior + status)
        self._f_clima = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self._f_city = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self._f_title_status = tkfont.Font(family="Segoe UI", size=13, weight="bold")

        self._f_temp = tkfont.Font(family="Segoe UI", size=34, weight="bold")
        self._f_tag = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self._f_forecast = tkfont.Font(family="Segoe UI", size=18, weight="bold")

        # Estado (textos)
        self._city_text = "ALFENAS"
        self._temp_text = "—°C"
        self._live_status_text = "—"          # vai pro topo (direita)
        self._temp_tag_text = "TEMP. AGORA"   # vira CACHE HH:MM / OFFLINE quando necessário
        self._forecast_line_text = "Amanhã: —"

        # robustez de símbolo/ícone
        self._symbol_code: Optional[str] = None
        self._last_good_symbol_code: Optional[str] = None
        self._last_official_icon_path: Optional[str] = None

        # Background cache
        self._bg_img = None
        self._bg_key = None

        # Icon cache
        self._icon_img = None
        self._icon_key = None
        self._icon_path_pending: Optional[str] = None

        # IDs / layout
        self._ids: Dict[str, int] = {}
        self._layout_geom = None
        self._title_geom: Optional[Dict[str, int]] = None
        self._last_size = (0, 0)
        self._redraw_after = None

        # -------------------------
        # TOP STATUS marquee (CLIP REAL via create_window)
        # -------------------------
        self._tmarquee_win_id: Optional[int] = None
        self._tmarquee_frame: Optional[tk.Frame] = None
        self._tmarquee_label1: Optional[tk.Label] = None
        self._tmarquee_label2: Optional[tk.Label] = None
        self._tmarquee_after = None
        self._tmarquee_running = False
        self._tmarquee_x1 = 0
        self._tmarquee_x2 = 0
        self._tmarquee_gap_px = 60
        self._tmarquee_tick_ms = 25
        self._tmarquee_speed_px = 1
        self._tmarquee_last_box: Optional[Tuple[int, int, int, int]] = None  # (x1,y1,x2,y2)

        # -------------------------
        # Forecast marquee (CLIP REAL via create_window)
        # -------------------------
        self._forecast_frame: Optional[tk.Frame] = None
        self._forecast_label: Optional[tk.Label] = None
        self._forecast_win_id: Optional[int] = None
        self._forecast_label2: Optional[tk.Label] = None

        self._marquee_x2 = 0
        self._marquee_after = None
        self._marquee_running = False
        self._marquee_x = 0
        self._marquee_speed_px = MS_MARQUEE_SPEED_PX
        self._marquee_tick_ms = MS_MARQUEE_TICK
        self._marquee_gap_px = 110
        self._marquee_last_box: Optional[Tuple[int, int, int, int]] = None  # (x1,y1,x2,y2)

        self.canvas.bind("<Configure>", self._on_configure)
        self._disposed = False
        self._schedule_redraw(full=True)

    # -------------------------
    # Helpers
    # -------------------------

    def _blend_hex(self, a: str, b: str, t: float) -> str:
        try:
            a = (a or "#000000").strip()
            b = (b or "#000000").strip()
            if not a.startswith("#"):
                a = "#" + a
            if not b.startswith("#"):
                b = "#" + b

            t = float(t)
            t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)

            ar = int(a[1:3], 16); ag = int(a[3:5], 16); ab = int(a[5:7], 16)
            br = int(b[1:3], 16); bg = int(b[3:5], 16); bb = int(b[5:7], 16)

            rr = int(ar + (br - ar) * t)
            rg = int(ag + (bg - ag) * t)
            rb = int(ab + (bb - ab) * t)

            return f"#{rr:02x}{rg:02x}{rb:02x}"
        except Exception:
            return a if a else "#000000"

    def _forecast_clean_for_ui(self, s: str) -> str:
        t = (s or "").strip()
        if not t:
            return "—"
        t = " ".join(t.split())
        return t if t else "—"

    def _fallback_pin_path(self) -> Optional[str]:
        p = _img_path_try("CLUBAL_ICO") or _img_path_try("CLUBAL_ICO.png")
        if p and os.path.exists(p):
            return p
        p = _img_path_try("logo_sesi") or _img_path_try("logo_sesi.png")
        if p and os.path.exists(p):
            return p
        return None

    def _extract_now_desc_from_today_label(self, today_label: str) -> str:
        s = (today_label or "").strip()
        if not s:
            return "—"
        if ":" in s:
            tail = s.split(":", 1)[1].strip()
            return tail if tail else "—"
        return s
    
    def _weather_icon_code_candidates(self, symbol_code: Optional[str], is_day: bool) -> List[str]:
        if not symbol_code:
            return []

        s = str(symbol_code).strip().lower()
        if not s:
            return []

        if s.endswith("_day") or s.endswith("_night") or s.endswith("_polartwilight"):
            return [s]

        suf = "day" if is_day else "night"

        out = [s, f"{s}_{suf}"]
        seen = set()
        final = []

        for item in out:
            if item and item not in seen:
                seen.add(item)
                final.append(item)

        return final

    def _cached_weather_icon_path(self, symbol_code: Optional[str], is_day: bool) -> Optional[str]:
        candidates = self._weather_icon_code_candidates(symbol_code, is_day)
        if not candidates:
            return None

        weather_icons_dir = None

        try:
            ctx = getattr(self, "ctx", None)
            paths = getattr(ctx, "paths", None) if ctx is not None else None
            cache_dir = getattr(paths, "cache_dir", None) if paths is not None else None

            if cache_dir is not None:
                weather_icons_dir = os.path.join(
                    str(cache_dir),
                    "weather",
                    "weather_icons",
                )
        except Exception:
            weather_icons_dir = None

        if not weather_icons_dir or not os.path.isdir(weather_icons_dir):
            return None

        for code in candidates:
            p = os.path.join(weather_icons_dir, f"{code}.png")
            if os.path.exists(p):
                return p

        return None

    # -------------------------
    # TOP marquee (status direita) — CLIP REAL
    # -------------------------

    def _stop_top_marquee(self) -> None:
        try:
            if self._tmarquee_after is not None:
                self.after_cancel(self._tmarquee_after)
        except Exception:
            pass
        self._tmarquee_after = None
        self._tmarquee_running = False

    def _ensure_top_marquee_widgets(self, bg: str) -> None:
        if self._tmarquee_frame is not None and self._tmarquee_label1 is not None and self._tmarquee_label2 is not None:
            return

        self._tmarquee_frame = tk.Frame(self.canvas, bg=bg, bd=0, highlightthickness=0)

        self._tmarquee_label1 = tk.Label(
            self._tmarquee_frame,
            text="",
            font=self._f_title_status,
            fg="#bcd3ff",
            bg=bg,
            bd=0,
            highlightthickness=0
        )
        self._tmarquee_label1.place(x=0, y=0)

        self._tmarquee_label2 = tk.Label(
            self._tmarquee_frame,
            text="",
            font=self._f_title_status,
            fg="#bcd3ff",
            bg=bg,
            bd=0,
            highlightthickness=0
        )
        self._tmarquee_label2.place(x=0, y=0)

    def _layout_top_status_right(self, box: Tuple[int, int, int, int], text: str, bg: str) -> None:
        """
        box: (x1,y1,x2,y2) área do status (direita). Deve ser CLIP real.
        - Se couber: mostra estático alinhado à direita.
        - Se não couber: marquee contínuo rolando para a esquerda.
        """
        x1, y1, x2, y2 = box
        w = max(10, int(x2 - x1))
        h = max(10, int(y2 - y1))

        self._ensure_top_marquee_widgets(bg=bg)

        if self._tmarquee_frame is None or self._tmarquee_label1 is None or self._tmarquee_label2 is None:
            return

        top_label1 = self._tmarquee_label1
        top_label2 = self._tmarquee_label2

        try:
            if self._tmarquee_win_id is None:
                self._tmarquee_win_id = self.canvas.create_window(
                    x1, y1, anchor="nw",
                    window=self._tmarquee_frame,
                    width=w,
                    height=h
                )
            else:
                self.canvas.coords(self._tmarquee_win_id, x1, y1)
                self.canvas.itemconfig(self._tmarquee_win_id, width=w, height=h)
        except Exception:
            return

        safe_text = (" ".join((text or "").split()) or "—").upper()

        try:
            top_label1.configure(text=safe_text, font=self._f_title_status, bg=bg)
            top_label2.configure(text=safe_text, font=self._f_title_status, bg=bg)
        except Exception:
            return

        try:
            text_w = int(self._f_title_status.measure(safe_text))
        except Exception:
            text_w = len(safe_text) * 9

        try:
            line_h = int(self._f_title_status.metrics("linespace"))
        except Exception:
            line_h = 18

        y_center = int(max(0, (h - line_h) // 2))
        self._tmarquee_last_box = box

        if text_w <= (w - 6):
            self._stop_top_marquee()

            x_right = int(max(0, w - text_w))
            try:
                top_label1.place_configure(x=x_right, y=y_center)
                top_label2.place_configure(x=w + 2000, y=y_center)
            except Exception:
                pass
            return

        self._stop_top_marquee()
        self._tmarquee_running = True

        spacing = int(max(40, min(int(self._tmarquee_gap_px), max(40, w // 2))))

        self._tmarquee_x1 = int(w + 2)
        self._tmarquee_x2 = int(self._tmarquee_x1 + text_w + spacing)

        try:
            top_label1.place_configure(x=self._tmarquee_x1, y=y_center)
            top_label2.place_configure(x=self._tmarquee_x2, y=y_center)
        except Exception:
            pass

        def _tick():
            if not self._tmarquee_running:
                return
            if self._tmarquee_last_box != box:
                return

            step = int(max(1, self._tmarquee_speed_px))
            self._tmarquee_x1 -= step
            self._tmarquee_x2 -= step

            if (self._tmarquee_x1 + text_w) < -2:
                self._tmarquee_x1 = int(self._tmarquee_x2 + text_w + spacing)
            if (self._tmarquee_x2 + text_w) < -2:
                self._tmarquee_x2 = int(self._tmarquee_x1 + text_w + spacing)

            try:
                top_label1.place_configure(x=self._tmarquee_x1)
                top_label2.place_configure(x=self._tmarquee_x2)
            except Exception:
                pass

            self._tmarquee_after = self.after(int(self._tmarquee_tick_ms), _tick)

        self._tmarquee_after = self.after(int(self._tmarquee_tick_ms), _tick)

    # -------------------------
    # Forecast marquee (CLIP REAL)
    # -------------------------

    def _stop_marquee(self) -> None:
        try:
            if self._marquee_after is not None:
                self.after_cancel(self._marquee_after)
        except Exception:
            pass
        self._marquee_after = None
        self._marquee_running = False

    def _ensure_forecast_marquee_widgets(self) -> None:
        if self._forecast_frame is not None and self._forecast_label is not None and self._forecast_label2 is not None:
            return

        bg = getattr(self, "_forecast_strip_bg", self.glass_fill)
        edge = getattr(self, "_forecast_strip_edge", self.glass_edge)

        self._forecast_frame = tk.Frame(self.canvas, bg=bg, bd=0, highlightthickness=1, highlightbackground=edge)
        self._forecast_label = tk.Label(
            self._forecast_frame,
            text="",
            font=self._f_forecast,
            fg="#ffffff",
            bg=bg,
            bd=0,
            highlightthickness=0
        )
        self._forecast_label.place(x=0, y=0)

        self._forecast_label2 = tk.Label(
            self._forecast_frame,
            text="",
            font=self._f_forecast,
            fg="#ffffff",
            bg=bg,
            bd=0,
            highlightthickness=0
        )
        self._forecast_label2.place(x=0, y=0)

    def _start_or_layout_marquee(self, box: Tuple[int, int, int, int], text: str) -> None:
        x1, y1, x2, y2 = box
        w = max(10, int(x2 - x1))
        h = max(10, int(y2 - y1))

        self._ensure_forecast_marquee_widgets()

        if self._forecast_frame is None or self._forecast_label is None or self._forecast_label2 is None:
            return

        forecast_label1 = self._forecast_label
        forecast_label2 = self._forecast_label2

        try:
            if self._forecast_win_id is None:
                self._forecast_win_id = self.canvas.create_window(
                    x1, y1, anchor="nw",
                    window=self._forecast_frame,
                    width=w,
                    height=h
                )
            else:
                self.canvas.coords(self._forecast_win_id, x1, y1)
                self.canvas.itemconfig(self._forecast_win_id, width=w, height=h)
        except Exception:
            return

        safe_text = " ".join((text or "").split()) or "—"

        try:
            forecast_label1.configure(text=safe_text, font=self._f_forecast)
            forecast_label2.configure(text=safe_text, font=self._f_forecast)
        except Exception:
            return

        try:
            text_w = int(self._f_forecast.measure(safe_text))
        except Exception:
            text_w = len(safe_text) * 10

        try:
            line_h = int(self._f_forecast.metrics("linespace"))
        except Exception:
            line_h = 26

        y_center = int(max(0, (h - line_h) // 2))
        self._marquee_last_box = box

        if text_w <= (w - 10):
            self._stop_marquee()
            x_center = int(max(0, (w - text_w) // 2))
            try:
                forecast_label1.place_configure(x=x_center, y=y_center)
                forecast_label2.place_configure(x=w + 2000, y=y_center)
            except Exception:
                pass
            return

        self._stop_marquee()
        self._marquee_running = True

        spacing = int(max(40, min(int(self._marquee_gap_px), max(40, w // 2))))

        self._marquee_x = int(w + 2)
        self._marquee_x2 = int(self._marquee_x + text_w + spacing)

        try:
            forecast_label1.place_configure(x=self._marquee_x, y=y_center)
            forecast_label2.place_configure(x=self._marquee_x2, y=y_center)
        except Exception:
            pass

        def _tick():
            if not self._marquee_running:
                return
            if self._marquee_last_box != box:
                return

            step = int(max(1, self._marquee_speed_px))

            self._marquee_x -= step
            self._marquee_x2 -= step

            if (self._marquee_x + text_w) < -2:
                self._marquee_x = int(self._marquee_x2 + text_w + spacing)
            if (self._marquee_x2 + text_w) < -2:
                self._marquee_x2 = int(self._marquee_x + text_w + spacing)

            try:
                forecast_label1.place_configure(x=self._marquee_x)
                forecast_label2.place_configure(x=self._marquee_x2)
            except Exception:
                pass

            self._marquee_after = self.after(int(self._marquee_tick_ms), _tick)

        self._marquee_after = self.after(int(self._marquee_tick_ms), _tick)

    # -------------------------
    # Icon async
    # -------------------------

    def _icon_worker(self, symbol_code: Optional[str], is_day: bool):
        icon_path = None

        # ctx pode não existir em alguns cenários (refactors / init parcial)
        ctx_obj = getattr(self, "ctx", None)
        app_dir = ""
        try:
            if ctx_obj is not None and getattr(ctx_obj, "paths", None) is not None:
                if getattr(ctx_obj.paths, "app_dir", None) is not None:
                    app_dir = str(ctx_obj.paths.app_dir)
        except Exception:
            app_dir = ""

        try:
            icon_path = weather_mod.get_official_icon_png_path(
                symbol_code=symbol_code,
                is_day=is_day,
                app_dir=app_dir,
                logger=log,
                user_agent="CLUBAL-AgendaLive/2.0 (contact: local)",
            )
        except Exception as e:
            log(f"[WEATHER][ICON] worker exception {type(e).__name__}: {e}")
            icon_path = None

        if not icon_path:
            try:
                icon_path = self._cached_weather_icon_path(symbol_code, is_day)
                if icon_path:
                    log(f"[WEATHER][ICON] cache hit path={icon_path}")
            except Exception as e:
                log(f"[WEATHER][ICON] cache lookup exception {type(e).__name__}: {e}")
                icon_path = None

        def _apply():
            if (self._symbol_code or None) != (symbol_code or None):
                return
            if getattr(self, "_disposed", False):
                return

            if icon_path and os.path.exists(icon_path):
                self._icon_path_pending = icon_path
                self._last_official_icon_path = icon_path
                if symbol_code:
                    self._last_good_symbol_code = symbol_code

                self._update_icon(icon_path)
                self._place_icon()
                log(f"[WEATHER][ICON] applied path={icon_path}")
                return

            if self._last_official_icon_path and os.path.exists(self._last_official_icon_path):
                self._icon_path_pending = self._last_official_icon_path
                self._update_icon(self._last_official_icon_path)
                self._place_icon()
                log(f"[WEATHER][ICON] reused last path={self._last_official_icon_path}")
                return

            fallback_path = self._fallback_pin_path()
            self._icon_path_pending = fallback_path
            self._update_icon(fallback_path)
            self._place_icon()
            log(f"[WEATHER][ICON] fallback pin path={fallback_path}")

        try:
            self.after(0, _apply)
        except Exception:
            pass

    # -------------------------
    # Public setter
    # -------------------------

    def set_weather(self, city: str, res: weather_mod.WeatherResult):
        self._city_text = (str(city).strip().upper() if city else "LOCAL") or "LOCAL"
        self._temp_text = f"{res.temp_c}°C" if res.temp_c is not None else "—°C"

        self._live_status_text = (self._extract_now_desc_from_today_label(getattr(res, "today_label", "") or "") or "—").strip().upper()

        raw_forecast = (getattr(res, "tomorrow_label", None) or "Amanhã: —").strip()
        self._forecast_line_text = self._forecast_clean_for_ui(raw_forecast)

        incoming_sym = getattr(res, "symbol_code", None)
        if incoming_sym:
            self._symbol_code = incoming_sym
            self._last_good_symbol_code = incoming_sym
        else:
            self._symbol_code = self._last_good_symbol_code

        if getattr(res, "ok", False) and getattr(res, "source", "") != "cache":
            self._temp_tag_text = "TEMP. AGORA"
        else:
            if getattr(res, "cache_ts", None):
                hhmm = time.strftime("%H:%M", time.localtime(res.cache_ts))
                self._temp_tag_text = f"CACHE {hhmm}"
            else:
                self._temp_tag_text = "OFFLINE"

        base_icon_path = None

        if self._symbol_code:
            try:
                base_icon_path = self._cached_weather_icon_path(self._symbol_code, self.is_day_theme)
            except Exception:
                base_icon_path = None

        if not base_icon_path and self._last_official_icon_path and os.path.exists(self._last_official_icon_path):
            base_icon_path = self._last_official_icon_path

        if not base_icon_path:
            base_icon_path = self._fallback_pin_path()

        self._icon_path_pending = base_icon_path
        self._update_icon(base_icon_path)
        self._place_icon()

        self._update_text_items()

        try:
            if self._symbol_code:
                log(f"[WEATHER][ICON] start async symbol_code={self._symbol_code} is_day={self.is_day_theme}")
                th = threading.Thread(
                    target=self._icon_worker,
                    args=(self._symbol_code, self.is_day_theme),
                    daemon=True
                )
                th.start()
            else:
                log("[WEATHER][ICON] no symbol_code available; using cached/fallback")
        except Exception as e:
            log(f"[WEATHER][ICON] thread start failed {type(e).__name__}: {e}")

    # -------------------------
    # Redraw strategy
    # -------------------------

    def _on_configure(self, _evt=None):
        self._schedule_redraw(full=True)

    def _schedule_redraw(self, full: bool):
        if self._redraw_after is not None:
            try:
                self.after_cancel(self._redraw_after)
            except Exception:
                pass
            self._redraw_after = None
        self._redraw_after = self.after(60, lambda: self._redraw(full=full))

    def _redraw(self, full: bool):
        self._redraw_after = None

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 20 or h <= 20:
            return

        size = (w, h)
        if full and size == self._last_size:
            full = False
        else:
            self._last_size = size

        try:
            if full:
                self.canvas.delete("all")
                self._ids.clear()
                self._layout_geom = None
                self._title_geom = None

                # stop marquees
                self._stop_marquee()
                self._stop_top_marquee()

                # remove forecast window/widgets
                try:
                    if self._forecast_win_id is not None:
                        self.canvas.delete(self._forecast_win_id)
                except Exception:
                    pass
                self._forecast_win_id = None
                try:
                    if self._forecast_label is not None:
                        self._forecast_label.destroy()
                except Exception:
                    pass
                self._forecast_label = None
                try:
                    if self._forecast_label2 is not None:
                        self._forecast_label2.destroy()
                except Exception:
                    pass
                self._forecast_label2 = None
                try:
                    if self._forecast_frame is not None:
                        self._forecast_frame.destroy()
                except Exception:
                    pass
                self._forecast_frame = None
                self._marquee_last_box = None

                # remove top marquee window/widgets
                try:
                    if self._tmarquee_win_id is not None:
                        self.canvas.delete(self._tmarquee_win_id)
                except Exception:
                    pass
                self._tmarquee_win_id = None
                try:
                    if self._tmarquee_label1 is not None:
                        self._tmarquee_label1.destroy()
                except Exception:
                    pass
                self._tmarquee_label1 = None
                try:
                    if self._tmarquee_label2 is not None:
                        self._tmarquee_label2.destroy()
                except Exception:
                    pass
                self._tmarquee_label2 = None
                try:
                    if self._tmarquee_frame is not None:
                        self._tmarquee_frame.destroy()
                except Exception:
                    pass
                self._tmarquee_frame = None
                self._tmarquee_last_box = None

                self._draw_background(w, h)
                self._draw_frame(w, h)
                self._draw_layout(w, h)

                if self._icon_path_pending:
                    self._update_icon(self._icon_path_pending)
                self._place_icon()

                self._update_text_items()

            else:
                self._update_text_items()
                self._place_icon()

        except Exception:
            try:
                log("[WEATHER][UI] draw exception:\n" + traceback.format_exc())
            except Exception:
                pass

            self.canvas.delete("all")
            self._ids.clear()
            self._layout_geom = None
            self._title_geom = None
            self.canvas.create_rectangle(0, 0, w, h, fill=self.base_bg, outline="")
            self._draw_frame(w, h)

    # -------------------------
    # Drawing
    # -------------------------

    def _pil_cover_to_size(self, p: str, w: int, h: int):
        im = _pil_open_rgba(p)
        iw, ih = im.size
        if iw <= 0 or ih <= 0:
            return None

        scale = max(w / iw, h / ih)
        nw = max(1, int(iw * scale))
        nh = max(1, int(ih * scale))
        im = im.resize((nw, nh), PIL_LANCZOS)

        left = max(0, (nw - w) // 2)
        top = max(0, (nh - h) // 2)
        im = im.crop((left, top, left + w, top + h))

        return _pil_photo_image(im)

    def _draw_background(self, w: int, h: int):
        bg_name = "weather_day" if self.is_day_theme else "weather_night"
        p = _img_path_try(bg_name)

        try:
            log(f"[WEATHER][BG] PIL_OK={PIL_OK} bg_name={bg_name} path={p} exists={bool(p and os.path.exists(p))}")
        except Exception:
            pass

        key = (p, w, h, "PIL" if PIL_OK else "TK")
        if key != self._bg_key:
            self._bg_key = key
            self._bg_img = None

            if p and os.path.exists(p):
                if PIL_OK:
                    try:
                        self._bg_img = self._pil_cover_to_size(p, w, h)
                        try:
                            log(f"[WEATHER][BG] loaded via PIL size={w}x{h}")
                        except Exception:
                            pass
                    except Exception:
                        self._bg_img = None
                        try:
                            log("[WEATHER][BG] PIL load failed:\n" + traceback.format_exc())
                        except Exception:
                            pass

                if self._bg_img is None:
                    try:
                        img = tk.PhotoImage(file=p)
                        if img.width() > w or img.height() > h:
                            fx = max(1, img.width() // max(1, w))
                            fy = max(1, img.height() // max(1, h))
                            f = max(fx, fy)
                            img = img.subsample(f)
                        self._bg_img = img
                        try:
                            log(f"[WEATHER][BG] loaded via TK orig={img.width()}x{img.height()} canvas={w}x{h}")
                        except Exception:
                            pass
                    except Exception:
                        self._bg_img = None
                        try:
                            log("[WEATHER][BG] TK PhotoImage load failed:\n" + traceback.format_exc())
                        except Exception:
                            pass

        if self._bg_img:
            self.canvas.create_image(0, 0, anchor="nw", image=self._bg_img)
        else:
            self.canvas.create_rectangle(0, 0, w, h, fill=self.base_bg, outline="")

        if self._bg_img:
            self.canvas.create_image(0, 0, anchor="nw", image=self._bg_img)
        else:
            self.canvas.create_rectangle(0, 0, w, h, fill=self.base_bg, outline="")

    def _draw_frame(self, w: int, h: int):
        pad = 6
        self.canvas.create_rectangle(pad, pad, w - pad, h - pad, outline=self.border, width=2)
        self.canvas.create_line(pad + 2, pad + 2, w - pad - 2, pad + 2, fill=self.line_soft, width=2)

    def _glass_panel(self, x1, y1, x2, y2):
        w = int(max(1, x2 - x1))
        h = int(max(1, y2 - y1))

        if not PIL_OK:
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=self.glass_fill, outline="")
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=self.glass_edge, width=1)
            inset = 2
            self.canvas.create_rectangle(x1 + inset, y1 + inset, x2 - inset, y2 - inset, outline=self.glass_low, width=1)
            self.canvas.create_line(x1 + 3, y1 + 3, x2 - 3, y1 + 3, fill=self.glass_high, width=1)
            return

        alpha = int(max(35, min(180, getattr(self, "_glass_alpha", 105))))
        key = (w, h, alpha)

        img = self._glass_img_cache.get(key)

        if img is None:
            try:
                base_hex = (self.glass_fill or "#0a2a55").lstrip("#")
                r = int(base_hex[0:2], 16)
                g = int(base_hex[2:4], 16)
                b = int(base_hex[4:6], 16)

                im = _pil_new_rgba((w, h), (r, g, b, alpha))

                top_boost = 22
                bot_drop = 18
                for yy in range(h):
                    t = yy / max(1, (h - 1))
                    rr = int(r + (top_boost * (1.0 - t)) - (bot_drop * t))
                    gg = int(g + (top_boost * (1.0 - t)) - (bot_drop * t))
                    bb = int(b + (top_boost * (1.0 - t)) - (bot_drop * t))
                    rr = max(0, min(255, rr))
                    gg = max(0, min(255, gg))
                    bb = max(0, min(255, bb))
                    im.putpixel((0, yy), (rr, gg, bb, alpha))

                col = im.crop((0, 0, 1, h)).resize((w, h), PIL_NEAREST)
                img = _pil_photo_image(col)
                self._glass_img_cache[key] = img
            except Exception:
                img = None
                self._glass_img_cache[key] = None

        if img is not None:
            self._glass_img_refs.append(img)
            if len(self._glass_img_refs) > 60:
                self._glass_img_refs = self._glass_img_refs[-30:]
            self.canvas.create_image(x1, y1, anchor="nw", image=img)
        else:
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=self.glass_fill, outline="")

        self.canvas.create_rectangle(x1, y1, x2, y2, outline=self.glass_edge, width=1)
        inset = 2
        self.canvas.create_rectangle(x1 + inset, y1 + inset, x2 - inset, y2 - inset, outline=self.glass_low, width=1)
        self.canvas.create_line(x1 + 3, y1 + 3, x2 - 3, y1 + 3, fill=self.glass_high, width=1)

    def _draw_layout(self, w: int, h: int):
        pad = 12
        usable_h = max(1, h - 2 * pad - 18)
        usable_w = max(1, w - 2 * pad)

        # Tipografia topo + blocos
        clima_sz = int(max(10, min(13, usable_h * 0.050)))
        city_sz = int(max(14, min(22, usable_h * 0.080)))
        status_sz = int(max(10, min(14, city_sz - 4)))

        temp_sz = int(max(26, min(44, usable_h * 0.25)))
        tag_sz = int(max(10, min(12, usable_h * 0.045)))
        forecast_sz = int(max(14, min(22, usable_h * 0.090)))

        try:
            self._f_clima.configure(size=clima_sz)
            self._f_city.configure(size=city_sz)
            self._f_title_status.configure(size=status_sz)
            self._f_temp.configure(size=temp_sz)
            self._f_tag.configure(size=tag_sz)
            self._f_forecast.configure(size=forecast_sz)
        except Exception:
            pass

        # -------------------------
        # TOP PANEL (alinhado à esquerda + status à direita)
        # -------------------------
        title_h = int(max(44, min(64, usable_h * 0.20)))
        title_y1 = pad
        title_y2 = min(h - pad - 90, title_y1 + title_h)
        self._glass_panel(pad, title_y1, w - pad, title_y2)

        yc = (title_y1 + title_y2) // 2

        left_x = pad + 14
        right_x = w - pad - 14

        clima_text = "CLIMA"
        city_text = (self._city_text or "LOCAL").strip().upper()
        status_text = (self._live_status_text or "—").strip().upper()

        try:
            w_clima = int(self._f_clima.measure(clima_text))
        except Exception:
            w_clima = len(clima_text) * 8

        try:
            w_city = int(self._f_city.measure(city_text))
        except Exception:
            w_city = len(city_text) * 10

        gap_clima_city = 10
        gap_city_sep = 14
        gap_sep_status = 14
        min_gap_city_status = 18  # “respiro” entre ALFENAS e o bloco do status

        clima_x = left_x
        city_x = clima_x + w_clima + gap_clima_city

        # desenha esquerda
        self._ids["title_clima"] = self.canvas.create_text(
            clima_x, yc, anchor="w",
            text=clima_text,
            fill="#bcd3ff",
            font=self._f_clima
        )
        self._ids["title_city"] = self.canvas.create_text(
            city_x, yc, anchor="w",
            text=city_text,
            fill="#ffffff",
            font=self._f_city
        )

        sep_x = city_x + w_city + gap_city_sep
        self._ids["title_sep"] = self.canvas.create_text(
            sep_x, yc, anchor="w",
            text="|",
            fill="#1f5aa2" if self.is_day_theme else "#1a4476",
            font=self._f_title_status
        )

        # box do status: cresce para a esquerda, alinhado à direita do painel
        status_box_x1 = sep_x + gap_sep_status
        status_box_x2 = right_x

        # garante espaço mínimo (se a tela for muito estreita)
        min_status_box_w = 70
        if (status_box_x2 - status_box_x1) < min_status_box_w:
            status_box_x1 = max(sep_x + gap_sep_status, status_box_x2 - min_status_box_w)

        # se status invadir cidade, empurra o box para depois da cidade + respiro
        min_status_start = (city_x + w_city + min_gap_city_status + gap_city_sep + 10)
        if status_box_x1 < min_status_start:
            status_box_x1 = min_status_start
            if (status_box_x2 - status_box_x1) < min_status_box_w:
                status_box_x1 = max(sep_x + gap_sep_status, status_box_x2 - min_status_box_w)

        # guarda geometria do topo para updates
        self._title_geom = {
            "yc": yc,
            "left_x": left_x,
            "right_x": right_x,
            "clima_x": clima_x,
            "city_x": city_x,
            "sep_x": sep_x,
            "status_box_x1": int(status_box_x1),
            "status_box_x2": int(status_box_x2),
            "title_y1": int(title_y1),
            "title_y2": int(title_y2),
        }

        # status: alinhado à direita ou marquee (somente se não couber)
        # vamos usar marquee com CLIP real em um frame transparente (mesmo bg do glass)
        top_bg = self.glass_fill
        box_y1 = title_y1 + 6
        box_y2 = title_y2 - 6
        self._layout_top_status_right((int(status_box_x1), int(box_y1), int(status_box_x2), int(box_y2)), status_text, bg=top_bg)

        # -------------------------
        # CENTRAL: ÍCONE + TEMP (ícone mais destacado)
        # -------------------------
        title_gap = int(max(8, min(18, usable_h * 0.04)))
        mid_y1 = title_y2 + title_gap
        mid_y2 = h - pad - 4
        if mid_y2 < mid_y1 + 140:
            mid_y2 = mid_y1 + 140

        panel_y1 = mid_y1
        panel_y2 = mid_y2

        icon_box = int(min((panel_y2 - panel_y1), usable_w * 0.42))
        icon_box = max(92, min(icon_box, 190))

        icon_x1 = pad + 10
        icon_x2 = icon_x1 + icon_box
        icon_y1 = panel_y1
        icon_y2 = icon_y1 + icon_box
        self._glass_panel(icon_x1, icon_y1, icon_x2, icon_y2)

        text_x1 = icon_x2 + 12
        text_x2 = w - pad - 12
        text_y1 = icon_y1
        text_y2 = icon_y2
        if text_x2 < text_x1 + 170:
            text_x2 = text_x1 + 170
        self._glass_panel(text_x1, text_y1, text_x2, text_y2)

        safe_inset = 6

        icon_area_y1 = int(icon_y1 + 10 + safe_inset)
        icon_area_y2 = int(icon_y2 - 10 - safe_inset)
        icon_area_h = int(max(44, icon_area_y2 - icon_area_y1))
        icon_area_w = int(max(44, (icon_x2 - icon_x1) - 18))

        icon_target = int(min(icon_area_h, icon_area_w))
        icon_target = int(max(72, icon_target))
        icon_target = int(min(icon_target, icon_box - 14))

        icon_cx = int((icon_x1 + icon_x2) // 2)
        icon_cy = int(icon_area_y1 + (icon_area_h // 2))

        # tag temp
        ttag_h = max(20, min(30, (text_y2 - text_y1) // 6))
        ttag_x1 = text_x1 + 14 + safe_inset
        ttag_x2 = text_x2 - 14 - safe_inset
        ttag_y1 = text_y1 + 10 + safe_inset
        ttag_y2 = ttag_y1 + ttag_h

        tag_fill = "#0f3a77" if self.is_day_theme else "#0b2a55"
        tag_edge = "#1d5aa7" if self.is_day_theme else "#123d73"
        tag_txt = "#eaf2ff"

        pid2, tid2 = self._tag_bar(
            ttag_x1, ttag_y1, ttag_x2, ttag_y2,
            self._temp_tag_text, tag_fill, tag_edge, tag_txt, self._f_tag
        )
        self._ids["temp_tag_bg"] = pid2
        self._ids["temp_tag_text"] = tid2

        temp_cx = (text_x1 + text_x2) // 2
        temp_cy = (text_y1 + text_y2) // 2 + int(ttag_h * 0.25)
        self._ids["temp_text"] = self.canvas.create_text(
            temp_cx, temp_cy,
            anchor="center",
            text=self._temp_text,
            fill="#ffffff",
            font=self._f_temp,
            justify="center"
        )

        # -------------------------
        # BOTTOM: FORECAST (CLIP REAL)
        # -------------------------
        gap_bottom = 8
        bottom_y1 = icon_y2 + gap_bottom
        bottom_y2 = panel_y2
        if bottom_y2 < bottom_y1 + 70:
            bottom_y1 = max(icon_y2 + 6, bottom_y2 - 70)

        bottom_x1 = icon_x1
        bottom_x2 = text_x2
        self._glass_panel(bottom_x1, bottom_y1, bottom_x2, bottom_y2)

        text_pad_x = 12
        text_pad_y = 8
        mx1 = int(bottom_x1 + text_pad_x)
        mx2 = int(bottom_x2 - text_pad_x)
        my1 = int(bottom_y1 + text_pad_y)
        my2 = int(bottom_y2 - text_pad_y)

        self._start_or_layout_marquee((mx1, my1, mx2, my2), self._forecast_line_text)

        self._layout_geom = {
            "icon_box": (icon_x1, icon_y1, icon_x2, icon_y2),
            "icon_target": icon_target,
            "icon_center": (icon_cx, icon_cy),
        }

    def _tag_bar(self, x1: int, y1: int, x2: int, y2: int, text: str,
                 fill: str, edge: str, txt: str, font_obj: tkfont.Font):
        w = int(x2 - x1)
        h = int(y2 - y1)

        if w < 40 or h < 16:
            pid = self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=edge, width=1)
            tid = self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                                          text=(text or "").strip(), fill=txt, font=font_obj)
            return pid, tid

        r = max(8, min(14, h // 2))
        pts = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2 - r,
            x1, y1 + r,
        ]

        pid = self.canvas.create_polygon(pts, fill=fill, outline=edge, width=1, smooth=True)
        tid = self.canvas.create_text(
            (x1 + x2) // 2, (y1 + y2) // 2,
            anchor="center",
            text=(text or "").strip(),
            fill=txt,
            font=font_obj
        )
        return pid, tid

    def _update_text_items(self):
        # Atualiza esquerda do topo (CLIMA/CIDADE) e reposiciona se necessário via redraw leve
        try:
            if "title_city" in self._ids:
                self.canvas.itemconfig(self._ids["title_city"], text=(self._city_text or "LOCAL").strip().upper())
            if "title_clima" in self._ids:
                self.canvas.itemconfig(self._ids["title_clima"], text="CLIMA")
        except Exception:
            pass

        # Atualiza tag + temp
        try:
            if "temp_tag_text" in self._ids:
                self.canvas.itemconfig(self._ids["temp_tag_text"], text=(self._temp_tag_text or "TEMP. AGORA").strip())
            if "temp_text" in self._ids:
                self.canvas.itemconfig(self._ids["temp_text"], text=self._temp_text)
        except Exception:
            pass

        # Atualiza top status (direita): relayout do marquee usando a última box
        try:
            if self._title_geom:
                status_text = (self._live_status_text or "—").strip().upper()
                x1 = int(self._title_geom.get("status_box_x1", 0))
                x2 = int(self._title_geom.get("status_box_x2", 0))
                y1 = int(self._title_geom.get("title_y1", 0) + 6)
                y2 = int(self._title_geom.get("title_y2", 0) - 6)
                if x2 > x1 + 10 and y2 > y1 + 10:
                    self._layout_top_status_right((x1, y1, x2, y2), status_text, bg=self.glass_fill)
        except Exception:
            pass

        # Forecast: mantém clip correto
        try:
            if self._marquee_last_box:
                self._start_or_layout_marquee(self._marquee_last_box, self._forecast_line_text)
        except Exception:
            pass

    # -------------------------
    # Icon
    # -------------------------

    def _pil_icon_to_size(self, p: str, target: int):
        im = _pil_open_rgba(p)
        iw, ih = im.size
        if iw <= 0 or ih <= 0:
            return None
        scale = min(target / iw, target / ih)
        nw = max(1, int(iw * scale))
        nh = max(1, int(ih * scale))
        im = im.resize((nw, nh), PIL_LANCZOS)

        canvas = _pil_new_rgba((target, target), (0, 0, 0, 0))
        x = (target - nw) // 2
        y = (target - nh) // 2
        canvas.paste(im, (x, y), im)
        return _pil_photo_image(canvas)

    def _update_icon(self, icon_path: Optional[str]):
        if not icon_path or not os.path.exists(icon_path):
            self._icon_img = None
            self._icon_key = None
            return

        target = 112
        if self._layout_geom:
            try:
                target = int(self._layout_geom.get("icon_target", target))
            except Exception:
                target = target

        target = max(64, int(target))

        key = (icon_path, target, "PIL" if PIL_OK else "TK")
        if key == self._icon_key:
            return
        self._icon_key = key

        self._icon_img = None
        try:
            if PIL_OK:
                try:
                    self._icon_img = self._pil_icon_to_size(icon_path, target)
                except Exception:
                    self._icon_img = None

            if self._icon_img is None:
                img = tk.PhotoImage(file=icon_path)
                if img.width() > target or img.height() > target:
                    fx = max(1, img.width() // max(1, target))
                    fy = max(1, img.height() // max(1, target))
                    f = max(fx, fy)
                    img = img.subsample(f)
                self._icon_img = img
        except Exception:
            self._icon_img = None

    def _place_icon(self):
        if not self._layout_geom or "icon_box" not in self._layout_geom:
            return

        if "icon_img" in self._ids:
            try:
                self.canvas.delete(self._ids["icon_img"])
            except Exception:
                pass
            self._ids.pop("icon_img", None)

        if not self._icon_img:
            return

        try:
            cx, cy = self._layout_geom.get("icon_center", (None, None))
        except Exception:
            cx, cy = (None, None)

        if cx is None or cy is None:
            x1, y1, x2, y2 = self._layout_geom["icon_box"]
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

        self._ids["icon_img"] = self.canvas.create_image(int(cx), int(cy), anchor="center", image=self._icon_img)

    def dispose(self) -> None:
        self._disposed = True

        # stop marquees
        try:
            self._stop_marquee()
        except Exception:
            pass
        try:
            self._stop_top_marquee()
        except Exception:
            pass

        # cancel redraw
        try:
            redraw_after = getattr(self, "_redraw_after", None)
            if redraw_after is not None:
                try:
                    self.after_cancel(redraw_after)
                except Exception:
                    pass
            self._redraw_after = None
        except Exception:
            pass

        # cleanup forecast
        try:
            forecast_win_id = getattr(self, "_forecast_win_id", None)
            if forecast_win_id is not None:
                try:
                    self.canvas.delete(forecast_win_id)
                except Exception:
                    pass
            self._forecast_win_id = None
        except Exception:
            pass

        try:
            forecast_label = getattr(self, "_forecast_label", None)
            if forecast_label is not None:
                try:
                    forecast_label.destroy()
                except Exception:
                    pass
            self._forecast_label = None
        except Exception:
            pass

        try:
            forecast_label2 = getattr(self, "_forecast_label2", None)
            if forecast_label2 is not None:
                try:
                    forecast_label2.destroy()
                except Exception:
                    pass
            self._forecast_label2 = None
        except Exception:
            pass

        try:
            forecast_frame = getattr(self, "_forecast_frame", None)
            if forecast_frame is not None:
                try:
                    forecast_frame.destroy()
                except Exception:
                    pass
            self._forecast_frame = None
        except Exception:
            pass

        # cleanup top marquee
        try:
            tmarquee_win_id = getattr(self, "_tmarquee_win_id", None)
            if tmarquee_win_id is not None:
                try:
                    self.canvas.delete(tmarquee_win_id)
                except Exception:
                    pass
            self._tmarquee_win_id = None
        except Exception:
            pass

        try:
            tmarquee_label1 = getattr(self, "_tmarquee_label1", None)
            if tmarquee_label1 is not None:
                try:
                    tmarquee_label1.destroy()
                except Exception:
                    pass
            self._tmarquee_label1 = None
        except Exception:
            pass

        try:
            tmarquee_label2 = getattr(self, "_tmarquee_label2", None)
            if tmarquee_label2 is not None:
                try:
                    tmarquee_label2.destroy()
                except Exception:
                    pass
            self._tmarquee_label2 = None
        except Exception:
            pass

        try:
            tmarquee_frame = getattr(self, "_tmarquee_frame", None)
            if tmarquee_frame is not None:
                try:
                    tmarquee_frame.destroy()
                except Exception:
                    pass
            self._tmarquee_frame = None
        except Exception:
            pass

# -------------------------
# App (candidato a módulo: app.py)
# -------------------------

class ClubalApp(tk.Tk):
    def __init__(self):
        self.ctx = ctx
        super().__init__()

        # DPI / Tk scaling: estabiliza o mesmo layout em 1360x768 e 1920x1080 (com escalas diferentes)
        _force_tk_scaling_96dpi(self)

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
        self.weather_card = WeatherCard(self.right_center, is_day_theme=self.is_day_theme)

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
        _enable_windows_dpi_awareness()  # precisa ocorrer antes do Tk criar janelas
        _selftest_geometry(logger=log)
        ClubalApp().mainloop()
    except Exception:
        log("Fatal error:\n" + traceback.format_exc())