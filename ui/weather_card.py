from __future__ import annotations

import os
import time
import traceback
import threading
from typing import Dict, List, Optional, Tuple

import tkinter as tk
import tkinter.font as tkfont

from ui.theme import MS_MARQUEE_TICK, MS_MARQUEE_SPEED_PX
from ui.image_runtime import (
    PIL_OK,
    PIL_LANCZOS,
    PIL_NEAREST,
    img_path_try as _img_path_try,
    pil_new_rgba as _pil_new_rgba,
    pil_open_rgba as _pil_open_rgba,
    pil_photo_image as _pil_photo_image,
)

from ui.weather_card_marquee import (
    ensure_forecast_marquee_widgets,
    ensure_top_marquee_widgets,
    layout_top_status_right,
    start_or_layout_forecast_marquee,
    stop_forecast_marquee,
    stop_top_marquee,
)
import weather_service as weather_mod


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

    def __init__(self, master, is_day_theme: bool, *, ctx=None, logger=None):
        super().__init__(master, bd=0, highlightthickness=0)
        self.is_day_theme = is_day_theme
        self.ctx = ctx
        self._logger = logger

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


    def _log(self, msg: str) -> None:
        try:
            if self._logger is not None:
                self._logger(msg)
        except Exception:
            pass

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
        stop_top_marquee(self)

    def _ensure_top_marquee_widgets(self, bg: str) -> None:
        ensure_top_marquee_widgets(self, bg=bg)

    def _layout_top_status_right(self, box: Tuple[int, int, int, int], text: str, bg: str) -> None:
        layout_top_status_right(self, box=box, text=text, bg=bg)

    # -------------------------
    # Forecast marquee (CLIP REAL)
    # -------------------------

    def _stop_marquee(self) -> None:
        stop_forecast_marquee(self)

    def _ensure_forecast_marquee_widgets(self) -> None:
        ensure_forecast_marquee_widgets(self)

    def _start_or_layout_marquee(self, box: Tuple[int, int, int, int], text: str) -> None:
        start_or_layout_forecast_marquee(self, box=box, text=text)

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
                logger=self._log,
                user_agent="CLUBAL-AgendaLive/2.0 (contact: local)",
            )
        except Exception as e:
            self._log(f"[WEATHER][ICON] worker exception {type(e).__name__}: {e}")
            icon_path = None

        if not icon_path:
            try:
                icon_path = self._cached_weather_icon_path(symbol_code, is_day)
                if icon_path:
                    self._log(f"[WEATHER][ICON] cache hit path={icon_path}")
            except Exception as e:
                self._log(f"[WEATHER][ICON] cache lookup exception {type(e).__name__}: {e}")
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
                self._log(f"[WEATHER][ICON] applied path={icon_path}")
                return

            if self._last_official_icon_path and os.path.exists(self._last_official_icon_path):
                self._icon_path_pending = self._last_official_icon_path
                self._update_icon(self._last_official_icon_path)
                self._place_icon()
                self._log(f"[WEATHER][ICON] reused last path={self._last_official_icon_path}")
                return

            fallback_path = self._fallback_pin_path()
            self._icon_path_pending = fallback_path
            self._update_icon(fallback_path)
            self._place_icon()
            self._log(f"[WEATHER][ICON] fallback pin path={fallback_path}")

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
                self._log(f"[WEATHER][ICON] start async symbol_code={self._symbol_code} is_day={self.is_day_theme}")
                th = threading.Thread(
                    target=self._icon_worker,
                    args=(self._symbol_code, self.is_day_theme),
                    daemon=True
                )
                th.start()
            else:
                self._log("[WEATHER][ICON] no symbol_code available; using cached/fallback")
        except Exception as e:
            self._log(f"[WEATHER][ICON] thread start failed {type(e).__name__}: {e}")

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
                self._log("[WEATHER][UI] draw exception:\n" + traceback.format_exc())
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
            self._log(f"[WEATHER][BG] PIL_OK={PIL_OK} bg_name={bg_name} path={p} exists={bool(p and os.path.exists(p))}")
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
                            self._log(f"[WEATHER][BG] loaded via PIL size={w}x{h}")
                        except Exception:
                            pass
                    except Exception:
                        self._bg_img = None
                        try:
                            self._log("[WEATHER][BG] PIL load failed:\n" + traceback.format_exc())
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
                            self._log(f"[WEATHER][BG] loaded via TK orig={img.width()}x{img.height()} canvas={w}x{h}")
                        except Exception:
                            pass
                    except Exception:
                        self._bg_img = None
                        try:
                            self._log("[WEATHER][BG] TK PhotoImage load failed:\n" + traceback.format_exc())
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
