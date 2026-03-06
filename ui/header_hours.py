from __future__ import annotations

from typing import Any, Optional, Tuple

import time
import tkinter as tk
import tkinter.font as tkfont


class HoursCard(tk.Frame):
    """
    Card de horários (título + 2 sub-cards à esquerda + tabela de horários à direita)
    Compatível com ClubalApp:
      - self._mode
      - update_view(force=False)
      - tick_rotate()
    """

    def __init__(self, master, is_day_theme: bool, ctx=None, *, rounded_frame_cls: Any):
        super().__init__(master, bd=0, highlightthickness=0)
        self.is_day_theme = is_day_theme
        self.ctx = ctx
        self._rounded_frame_cls = rounded_frame_cls

        try:
            self.configure(bg=master["bg"])
        except Exception:
            pass

        self.pack_propagate(False)
        self.grid_propagate(False)

         # -------------------------
        # Paleta (dia/noite) — independente do WeatherCard
        # -------------------------
        if self.is_day_theme:
            self.card_bg = "#ffffff"
            self.border = "#cfd8e5"
            self.text = "#0b2d4d"
            self.soft = "#5c6f86"
            self.panel = "#e9eef5"
            self.panel2 = "#dde6f2"
            self.vline_col = "#cfd8e5"
            self.table_fg = "#0b2d4d"
            self.table_fg_soft = "#0b2d4d"
            self.guide_col = "#d6deea"

            # Top bar (neutral, cohesive with the global UI)
            self.topbar_bg = "#0b2d4d"
            self.topbar_fg = "#ffffff"

            # Status semantic colors (soft)
            self.status_open_bg1 = "#dff3ea"
            self.status_open_bg2 = "#d2eee2"
            self.status_open_fg = "#1f7a4a"

            self.status_closed_bg1 = "#f4e1e1"
            self.status_closed_bg2 = "#f0d7d7"
            self.status_closed_fg = "#b23b3b"
        else:
            self.card_bg = "#0b223c"
            self.border = "#132744"
            self.text = "#ffffff"
            self.soft = "#cfe2ff"
            self.panel = "#4b6277"
            self.panel2 = "#3c5266"
            self.vline_col = "#2c3f56"
            self.table_fg = "#ffffff"
            self.table_fg_soft = "#ffffff"
            self.guide_col = "#20324d"

            # Top bar (neutral)
            self.topbar_bg = "#132744"
            self.topbar_fg = "#ffffff"

            # Status semantic colors (soft, night-safe)
            self.status_open_bg1 = "#173a2b"
            self.status_open_bg2 = "#123024"
            self.status_open_fg = "#bfffe1"

            self.status_closed_bg1 = "#3b1f24"
            self.status_closed_bg2 = "#311a1f"
            self.status_closed_fg = "#ffd1d1"

        # -------------------------
        # Modos + horários (fonte da verdade)
        # -------------------------
        self.modes = [
            {
                "title": "ACADEMIA",
                "rows": [("SEG–QUI", "06:00–21:30"),
                         ("SEX",     "06:00–21:00"),
                         ("SÁB",     "08:00–12:00"),
                         ("DOM",     "FECHADO")],
                "schedule": {
                    "SEGQUI": ("06:00", "21:30"),
                    "SEX": ("06:00", "21:00"),
                    "SAB": ("08:00", "12:00"),
                    "DOMFER": None,
                },
            },
            {
                "title": "SECRETARIA",
                "rows": [("SEG–SEX", "08:00–20:00"),
                         ("SÁB",     "08:00–20:00"),
                         ("DOM/FER", "09:00–20:00")],
                "schedule": {
                    "SEGSEX": ("08:00", "20:00"),
                    "SAB": ("08:00", "20:00"),
                    "DOMFER": ("09:00", "20:00"),
                },
            },
            {
                "title": "CLUBE",
                "rows": [("SEG–SEX", "06:00–22:00"),
                         ("SÁB",     "08:00–20:00"),
                         ("DOM/FER", "09:00–20:00")],
                "schedule": {
                    "SEGSEX": ("06:00", "22:00"),
                    "SAB": ("08:00", "20:00"),
                    "DOMFER": ("09:00", "20:00"),
                },
            },
        ]
        self._mode = 0

        self.is_holiday = False

        # -------------------------
        # Micro-layout (dinâmico e seguro)
        # -------------------------
        self._row_pady = 2
        self._guide_pady = 9
        self._guide_padx = (10, 10)

        self._left_ratio_big = 0.58
        self._left_ratio_small = 0.38
        self._left_safe_ratio = 0.06

        self._big_font_min = 14
        self._big_font_max = 24
        self._small_font_min = 10
        self._small_font_max = 14
        self._table_font_min = 10
        self._table_font_max = 13

        # -------------------------
        # Container
        # -------------------------
        shadow_stipple = "gray25" if self.is_day_theme else "gray12"
        self.canvas = self._rounded_frame_cls(
            self,
            radius=18,
            bg=self.card_bg,
            border=self.border,
            shadow=True,
            shadow_offset=(3, 4),
            shadow_stipple=shadow_stipple,
        )
        self.canvas.pack(fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=self.card_bg)
        self.canvas.bind("<Configure>", self._place_inner)

        # -------------------------
        # Top bar
        # -------------------------
        self.top = tk.Frame(self.inner, bg=self.topbar_bg, height=34)
        self.top.pack(fill="x")
        self.top.pack_propagate(False)

        self.title_lbl = tk.Label(
            self.top,
            text="",
            font=("Segoe UI", 14, "bold"),
            fg=self.topbar_fg,
            bg=self.topbar_bg,
            anchor="center",
        )
        self.title_lbl.pack(fill="both", expand=True)

        # -------------------------
        # Body
        # -------------------------
        self.body = tk.Frame(self.inner, bg=self.card_bg)
        self.body.pack(fill="both", expand=True, padx=8, pady=8)

        self.body.grid_columnconfigure(0, weight=0)
        self.body.grid_columnconfigure(1, weight=0)
        self.body.grid_columnconfigure(2, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.left = tk.Frame(self.body, bg=self.card_bg)
        self.left.grid(row=0, column=0, sticky="nsew")
        self.left.grid_columnconfigure(0, weight=1)
        self.left.grid_rowconfigure(0, weight=3)
        self.left.grid_rowconfigure(1, weight=2)

        self.box1 = tk.Frame(self.left, bg=self.panel)
        self.box1.grid(row=0, column=0, sticky="nsew", pady=(0, 2))

        self._left_sep = tk.Frame(self.left, bg=self.border, height=1)
        self._left_sep.grid(row=0, column=0, sticky="sew")
        self._left_sep.lift()

        self.box2 = tk.Frame(self.left, bg=self.panel2)
        self.box2.grid(row=1, column=0, sticky="nsew")

        self.box1.grid_propagate(False)
        self.box2.grid_propagate(False)

        self.f_status_big = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self.f_status_small = tkfont.Font(family="Segoe UI", size=12, weight="bold")

        self.status_big = tk.Label(
            self.box1,
            text="",
            font=self.f_status_big,
            fg=self.text,
            bg=self.panel,
            anchor="w",
        )
        self.status_big.pack(fill="both", expand=True, padx=16)

        self.status_small = tk.Label(
            self.box2,
            text="",
            font=self.f_status_small,
            fg=self.text,
            bg=self.panel2,
            anchor="center",
        )
        self.status_small.pack(fill="both", expand=True, padx=6)

        self.vline = tk.Frame(self.body, bg=self.vline_col, width=2)
        self.vline.grid(row=0, column=1, sticky="ns", padx=10)

        self.right = tk.Frame(self.body, bg=self.card_bg)
        self.right.grid(row=0, column=2, sticky="nsew")

        self.table = tk.Frame(self.right, bg=self.card_bg)
        self.table.pack(fill="both", expand=True, padx=2, pady=2)

        self.row_labels = []
        self._table_rows = []

        self.f_table = tkfont.Font(family="Segoe UI", size=11, weight="bold")

        for _i in range(4):
            r = tk.Frame(self.table, bg=self.card_bg)
            r.pack(fill="x", pady=self._row_pady)

            r.grid_columnconfigure(0, weight=0)
            r.grid_columnconfigure(1, weight=1)
            r.grid_columnconfigure(2, weight=0)

            l_day = tk.Label(
                r,
                text="",
                font=self.f_table,
                width=8,
                fg=self.table_fg,
                bg=self.card_bg,
                anchor="w",
            )

            guide = tk.Frame(r, bg=self.guide_col, height=1)

            l_time = tk.Label(
                r,
                text="",
                font=self.f_table,
                width=11,
                fg=self.table_fg_soft,
                bg=self.card_bg,
                anchor="e",
            )

            l_day.grid(row=0, column=0, sticky="w")
            guide.grid(row=0, column=1, sticky="ew", padx=self._guide_padx, pady=self._guide_pady)
            l_time.grid(row=0, column=2, sticky="e")

            self.row_labels.append((l_day, l_time))
            self._table_rows.append((r, guide, l_day, l_time))

        self.update_view(force=True)

    def _mins(self, hhmm: str) -> Optional[int]:
        try:
            s = str(hhmm).strip()
            parts = s.split(":")
            if len(parts) < 2:
                return None
            hh = int(parts[0])
            mm = int(parts[1])
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                return hh * 60 + mm
        except Exception:
            pass
        return None

    def _today_key(self) -> str:
        wd = time.localtime().tm_wday
        if wd <= 3:
            return "SEGQUI"
        if wd == 4:
            return "SEX"
        if wd == 5:
            return "SAB"
        return "DOMFER"

    def _interval_for_today(self, schedule: dict) -> Optional[Tuple[int, int]]:
        key = self._today_key()
        if "SEGSEX" in schedule and key in ("SEGQUI", "SEX"):
            key = "SEGSEX"

        interval = schedule.get(key)
        if not interval:
            return None

        ini, fim = interval
        a = self._mins(ini)
        b = self._mins(fim)
        if a is None or b is None:
            return None
        return (a, b)

    def _next_opening_text(self, schedule: dict) -> str:
        wd0 = time.localtime().tm_wday
        for add in range(1, 8):
            wd = (wd0 + add) % 7
            if wd <= 3:
                k = "SEGQUI"
            elif wd == 4:
                k = "SEX"
            elif wd == 5:
                k = "SAB"
            else:
                k = "DOMFER"

            if "SEGSEX" in schedule and k in ("SEGQUI", "SEX"):
                k = "SEGSEX"

            interval = schedule.get(k)
            if interval:
                ini, _fim = interval
                dia = ["SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA", "SÁBADO", "DOMINGO"][wd]
                return f"ABRE {dia} ÀS {ini}"
        return "SEM PREVISÃO"

    def _fit_font_to_box(
        self,
        font_obj: tkfont.Font,
        text_sample: str,
        box_h: int,
        min_size: int,
        max_size: int,
        pad_v: int,
    ) -> None:
        try:
            if box_h <= 10:
                return

            target = int(max(min_size, min(max_size, int(font_obj.cget("size")))))
            try:
                font_obj.configure(size=target)
            except Exception:
                return

            for sz in range(target, min_size - 1, -1):
                try:
                    font_obj.configure(size=sz)
                    lh = int(font_obj.metrics("linespace"))
                except Exception:
                    lh = sz * 2

                if lh <= max(8, (box_h - pad_v)):
                    return

            try:
                font_obj.configure(size=min_size)
            except Exception:
                pass
        except Exception:
            pass

    def tick_rotate(self):
        self._mode = (self._mode + 1) % len(self.modes)
        self.update_view(force=True)

    def update_view(self, force: bool = False):
        mode = self.modes[self._mode]
        self.title_lbl.configure(text=mode["title"])

        rows = mode["rows"]

        for i, (row_frame, guide, l_day, l_time) in enumerate(self._table_rows):
            if i < len(rows):
                d, t = rows[i]
                l_day.configure(text=d)
                l_time.configure(text=t)

                try:
                    row_frame.pack_configure(pady=self._row_pady)
                except Exception:
                    pass

                if str(t).strip().upper() == "FECHADO":
                    guide.grid_remove()
                else:
                    guide.grid(row=0, column=1, sticky="ew", padx=self._guide_padx, pady=self._guide_pady)

                row_frame.pack(fill="x")
            else:
                guide.grid_remove()
                row_frame.pack_forget()

        def _apply_status_palette(kind: str) -> None:
            if kind == "open":
                bg1 = self.status_open_bg1
                bg2 = self.status_open_bg2
                fg = self.status_open_fg
            else:
                bg1 = self.status_closed_bg1
                bg2 = self.status_closed_bg2
                fg = self.status_closed_fg

            try:
                self.box1.configure(bg=bg1)
                self.box2.configure(bg=bg2)
            except Exception:
                pass

            try:
                self.status_big.configure(bg=bg1, fg=fg)
                self.status_small.configure(bg=bg2, fg=fg)
            except Exception:
                pass

        schedule = mode.get("schedule", {})
        now = time.localtime()
        now_m = now.tm_hour * 60 + now.tm_min

        interval = self._interval_for_today(schedule)

        if not interval:
            self.status_big.configure(text="FECHADO HOJE")
            self.status_small.configure(text="SEM ATENDIMENTO")
            _apply_status_palette("closed")
            return

        open_m, close_m = interval

        def fmt(m: int) -> str:
            return f"{m//60:02d}:{m%60:02d}"

        if open_m <= now_m < close_m:
            self.status_big.configure(text="ABERTO AGORA")
            self.status_small.configure(text=f"ATÉ {fmt(close_m)}")
            _apply_status_palette("open")
        elif now_m < open_m:
            self.status_big.configure(text="FECHADO AGORA")
            self.status_small.configure(text=f"ABRE ÀS {fmt(open_m)}")
            _apply_status_palette("closed")
        else:
            self.status_big.configure(text="FECHADO AGORA")
            self.status_small.configure(text=self._next_opening_text(schedule))
            _apply_status_palette("closed")

    def _place_inner(self, _evt=None):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 10 or h <= 10:
            return

        pad = 6
        self.canvas.delete("inner")
        self.canvas.create_window(
            pad,
            pad,
            anchor="nw",
            window=self.inner,
            width=max(10, w - 2 * pad),
            height=max(10, h - 2 * pad),
            tags=("inner",),
        )

        usable_h = max(1, h - 2 * pad - 34 - 16)

        table_sz = int(max(self._table_font_min, min(self._table_font_max, usable_h * 0.08)))
        big_sz = int(max(self._big_font_min, min(self._big_font_max, usable_h * 0.16)))
        small_sz = int(max(self._small_font_min, min(self._small_font_max, usable_h * 0.11)))

        try:
            self.f_table.configure(size=table_sz)
            self.f_status_big.configure(size=big_sz)
            self.f_status_small.configure(size=small_sz)
        except Exception:
            pass

        try:
            self._row_pady = int(max(2, min(6, (table_sz - 9) * 2 + 2)))
            self._guide_pady = int(max(7, min(11, 7 + (table_sz - 10))))
            self._guide_padx = (10, 10)

            for (row_frame, guide, _l_day, _l_time) in self._table_rows:
                try:
                    row_frame.pack_configure(pady=self._row_pady)
                except Exception:
                    pass
                try:
                    if guide.winfo_ismapped():
                        guide.grid_configure(padx=self._guide_padx, pady=self._guide_pady)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            self.body.update_idletasks()
            body_h = int(self.body.winfo_height() or usable_h)

            safe = int(max(8, min(24, body_h * self._left_safe_ratio)))

            left_h_raw = int(max(120, min(9999, body_h)))
            left_h = int(max(120, left_h_raw - (safe * 2)))

            gap = 2
            left_h = int(max(120, left_h - gap))

            box1_h = int(left_h * self._left_ratio_big)
            box2_h = int(left_h * self._left_ratio_small)

            box1_h = int(max(64, box1_h))
            box2_h = int(max(44, box2_h))

            total = box1_h + box2_h
            if total > left_h:
                overflow = total - left_h
                take = min(overflow, max(0, box1_h - 64))
                box1_h -= take
                overflow -= take
                if overflow > 0:
                    box2_h = max(44, box2_h - overflow)

            self.box1.configure(height=box1_h)
            self.box2.configure(height=box2_h)

            self._fit_font_to_box(
                font_obj=self.f_status_big,
                text_sample="FECHADO AGORA",
                box_h=box1_h,
                min_size=self._big_font_min,
                max_size=self._big_font_max,
                pad_v=18,
            )
            self._fit_font_to_box(
                font_obj=self.f_status_small,
                text_sample="ABRE QUINTA ÀS 06:00",
                box_h=box2_h,
                min_size=self._small_font_min,
                max_size=self._small_font_max,
                pad_v=14,
            )

        except Exception:
            pass

    def dispose(self) -> None:
        try:
            pass
        except Exception:
            pass