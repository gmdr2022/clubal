from __future__ import annotations

from typing import Any, List, Tuple

import tkinter as tk

from ui.theme import MS_SCROLL_TICK, MS_SECTION_SCROLL_SPEED_PX, SHADOW_MD


class SectionFrame(tk.Frame):
    """
    Seção (AGORA / PRÓXIMAS) com viewport + scroll vertical contínuo (bottom -> top),
    para não cortar quando houver muitas aulas no mesmo horário.

    - Usa Canvas como "janela" (clip real).
    - Mantém duas cópias (A e B) do mesmo conteúdo para loop sem “vazio”.
    - Só ativa o scroll quando o conteúdo excede a altura visível.
    """

    def __init__(
        self,
        master,
        title: str,
        is_day_theme: bool,
        *,
        rounded_frame_cls: Any,
        card_cls: Any,
    ):
        super().__init__(master, bd=0, highlightthickness=0)

        self._rounded_frame_cls = rounded_frame_cls
        self._card_cls = card_cls

        self.is_day_theme = bool(is_day_theme)
        self.title_text = (title or "").strip()
        self.kind = self.title_text.upper()

        self.bg = "#f5f7fb" if self.is_day_theme else "#06101f"
        self.panel_bg = "#f5f7fb" if self.is_day_theme else "#06101f"

        if self.is_day_theme:
            self.title_fg = "#1f7ab8" if self.kind != "AGORA" else "#1aa56a"
            self.line_fg = "#d5deea"
            self.panel_border = "#cfd8e5"
        else:
            self.title_fg = "#4aa3ff" if self.kind != "AGORA" else "#39d08a"
            self.line_fg = "#132744"
            self.panel_border = "#112645"

        self.configure(bg=self.bg)

        shadow_stipple = "gray25" if self.is_day_theme else "gray12"

        self.panel = self._rounded_frame_cls(
            self,
            radius=18,
            bg=self.panel_bg,
            border=self.panel_border,
            shadow=True,
            shadow_offset=SHADOW_MD,
            shadow_stipple=shadow_stipple,
        )
        self.panel.pack(fill="both", expand=True)

        self.inner = tk.Frame(self.panel, bg=self.panel_bg)
        self.inner.configure(
            highlightthickness=1,
            highlightbackground=("#d0d7e2" if self.is_day_theme else "#0c2038"),
            bd=0,
        )
        self.panel.bind("<Configure>", self._place_inner)

        header = tk.Frame(self.inner, bg=self.panel_bg)
        header.pack(fill="x", padx=14, pady=(12, 10))

        self.title_lbl = tk.Label(
            header,
            text=self.title_text,
            font=("Segoe UI", 18, "bold"),
            fg=self.title_fg,
            bg=self.panel_bg,
            anchor="w",
        )
        self.title_lbl.pack(side="left")

        self.line = tk.Frame(header, bg=self.line_fg, height=2)
        self.line.pack(side="left", fill="x", expand=True, padx=(12, 0), pady=12)

        self.grid_frame = tk.Frame(self.inner, bg=self.panel_bg)
        self.grid_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.grid_frame.grid_rowconfigure(0, weight=1)
        self.grid_frame.grid_columnconfigure(0, weight=1)

        self.scroll_canvas = tk.Canvas(
            self.grid_frame,
            bg=self.panel_bg,
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.scroll_canvas.grid(row=0, column=0, sticky="nsew")

        self.cards_host_a = tk.Frame(self.scroll_canvas, bg=self.panel_bg)
        self.cards_host_b = tk.Frame(self.scroll_canvas, bg=self.panel_bg)
        self.cards_host_a.grid_columnconfigure(0, weight=1)
        self.cards_host_b.grid_columnconfigure(0, weight=1)

        self._win_a = self.scroll_canvas.create_window(0, 0, anchor="nw", window=self.cards_host_a)
        self._win_b = self.scroll_canvas.create_window(0, 0, anchor="nw", window=self.cards_host_b)

        empty_fg = "#5c6f86" if self.is_day_theme else "#b9c7dd"
        self.empty_lbl = tk.Label(
            self.grid_frame,
            text="",
            font=("Segoe UI", 16, "bold"),
            fg=empty_fg,
            bg=self.panel_bg,
            anchor="center",
            justify="center",
        )
        self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center")
        self.empty_lbl.lift()

        self._max_cards_visible = 6
        self._padx = 10
        self._pady = 10
        self._card_h = 88
        self._card_w = 900

        self._scroll_after = None
        self._scroll_running = False
        self._scroll_y_a = 0
        self._scroll_y_b = 0
        self._scroll_speed_px = MS_SECTION_SCROLL_SPEED_PX
        self._scroll_tick_ms = MS_SCROLL_TICK
        self._content_h = 0
        self._viewport_h = 0
        self._last_viewport_w = 0

        if self.is_day_theme:
            theme = {
                "card_bg": "#ffffff",
                "card_fg": "#0b2d4d",
                "card_time_fg": "#0b2d4d",
                "card_status_fg": "#1b3a5f",
                "progress_bg": "#dfe7f2",
                "progress_fill": "#1F8A5B",
                "progress_fill_warn": "#F5A000",
                "progress_fill_crit": "#E34850",
                "progress_fill_upcoming": "#2B79D6",
                "pill_bg_default": "#1F8A5B",
                "pill_fg": "#06110C",
                "pill_bg_menor": "#C6A600",
                "pill_fg_menor": "#0B0B0B",
                "pill_bg_geral": "#1F8A5B",
                "pill_fg_geral": "#06110C",
                "card_pad_x": 18,
                "card_pad_y": 12,
            }
        else:
            theme = {
                "card_bg": "#0b223c",
                "card_fg": "#eaf2ff",
                "card_time_fg": "#eaf2ff",
                "card_status_fg": "#b9c7dd",
                "progress_bg": "#0F1E36",
                "progress_fill": "#38E8A4",
                "progress_fill_warn": "#FF9F1C",
                "progress_fill_crit": "#FF4D5E",
                "progress_fill_upcoming": "#3FA9FF",
                "pill_bg_default": "#39d08a",
                "pill_fg": "#06110C",
                "pill_bg_menor": "#C6A600",
                "pill_fg_menor": "#0B0B0B",
                "pill_bg_geral": "#39d08a",
                "pill_fg_geral": "#06110C",
                "card_pad_x": 18,
                "card_pad_y": 12,
            }

        self._theme = theme
        self._card_kind = "AGORA" if self.kind == "AGORA" else "PROXIMA"

        self.cards_a: List[Any] = []
        self.cards_b: List[Any] = []

        self._ensure_card_count(self._max_cards_visible)

        self.scroll_canvas.bind("<Configure>", self._on_viewport_resize)

    def _place_inner(self, _evt=None):
        w = self.panel.winfo_width()
        h = self.panel.winfo_height()
        if w <= 10 or h <= 10:
            return
        pad = 6
        self.panel.delete("inner")
        self.panel.create_window(
            pad,
            pad,
            anchor="nw",
            window=self.inner,
            width=max(10, w - 2 * pad),
            height=max(10, h - 2 * pad),
            tags=("inner",),
        )

    def _stop_scroll(self) -> None:
        try:
            if self._scroll_after is not None:
                self.after_cancel(self._scroll_after)
        except Exception:
            pass
        self._scroll_after = None
        self._scroll_running = False

    def _start_scroll(self) -> None:
        self._stop_scroll()

        if self._content_h <= 0 or self._viewport_h <= 0:
            return

        if self._content_h <= (self._viewport_h - 2):
            self._reposition_windows(static=True)
            return

        self._reposition_windows(static=False)
        self._scroll_running = True

        def _tick():
            if not self._scroll_running:
                return

            step = int(max(1, self._scroll_speed_px))

            self._scroll_y_a -= step
            self._scroll_y_b -= step

            if self._content_h > 0:
                if self._scroll_y_a <= -self._content_h:
                    self._scroll_y_a = self._scroll_y_b + self._content_h
                if self._scroll_y_b <= -self._content_h:
                    self._scroll_y_b = self._scroll_y_a + self._content_h

            try:
                self.scroll_canvas.coords(self._win_a, 0, int(self._scroll_y_a))
                self.scroll_canvas.coords(self._win_b, 0, int(self._scroll_y_b))
            except Exception:
                pass

            self._scroll_after = self.after(int(self._scroll_tick_ms), _tick)

        self._scroll_after = self.after(int(self._scroll_tick_ms), _tick)

    def _reposition_windows(self, static: bool) -> None:
        try:
            if static:
                self._scroll_y_a = 0
                self._scroll_y_b = self._content_h + 99999
            else:
                self._scroll_y_a = 0
                self._scroll_y_b = int(self._content_h)

            self.scroll_canvas.coords(self._win_a, 0, int(self._scroll_y_a))
            self.scroll_canvas.coords(self._win_b, 0, int(self._scroll_y_b))
        except Exception:
            pass

    def _on_viewport_resize(self, _evt=None):
        try:
            vw = int(self.scroll_canvas.winfo_width() or 0)
            vh = int(self.scroll_canvas.winfo_height() or 0)
            if vw <= 10 or vh <= 10:
                return

            self._viewport_h = vh
            self._last_viewport_w = vw

            new_w = max(260, vw - (self._padx * 2))
            if new_w != self._card_w:
                self._card_w = new_w
                for cc in (self.cards_a + self.cards_b):
                    try:
                        cc.configure(width=self._card_w, height=self._card_h)
                    except Exception:
                        pass

            self.scroll_canvas.itemconfig(self._win_a, width=vw)
            self.scroll_canvas.itemconfig(self._win_b, width=vw)

            self._recalc_content_height()
            self._start_scroll()

        except Exception:
            pass

    def _recalc_content_height(self) -> None:
        try:
            self.scroll_canvas.update_idletasks()

            bb = self.scroll_canvas.bbox(self._win_a)
            if not bb:
                self._content_h = 0
                return

            x1, y1, x2, y2 = bb
            h = int(max(0, (y2 - y1)))
            self._content_h = h
        except Exception:
            self._content_h = 0

    def _ensure_card_count(self, n: int) -> None:
        try:
            n = int(max(0, n))
        except Exception:
            n = 0

        while len(self.cards_a) < n:
            i = len(self.cards_a)
            cc = self._card_cls(
                self.cards_host_a,
                theme=self._theme,
                data={},
                card_kind=self._card_kind,
                width=self._card_w,
                height=self._card_h,
            )
            cc.grid(row=i, column=0, padx=self._padx, pady=self._pady, sticky="ew")
            self.cards_a.append(cc)

        while len(self.cards_b) < n:
            i = len(self.cards_b)
            cc = self._card_cls(
                self.cards_host_b,
                theme=self._theme,
                data={},
                card_kind=self._card_kind,
                width=self._card_w,
                height=self._card_h,
            )
            cc.grid(row=i, column=0, padx=self._padx, pady=self._pady, sticky="ew")
            self.cards_b.append(cc)

        for i in range(n, len(self.cards_a)):
            try:
                self.cards_a[i].grid_remove()
            except Exception:
                pass
        for i in range(n, len(self.cards_b)):
            try:
                self.cards_b[i].grid_remove()
            except Exception:
                pass

    def update_cards(self, card_data: List[Tuple]):
        total = int(len(card_data or []))

        if total <= 0:
            self._stop_scroll()
            if self.kind == "PRÓXIMAS":
                self.empty_lbl.configure(text="SEM PRÓXIMAS ATIVIDADES")
            else:
                self.empty_lbl.configure(text="SEM ATIVIDADES AGORA")
            self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center")
            self.empty_lbl.lift()

            self._ensure_card_count(self._max_cards_visible)
            for cc in (self.cards_a + self.cards_b):
                try:
                    cc.grid_remove()
                except Exception:
                    pass
            return

        try:
            self.empty_lbl.place_forget()
        except Exception:
            pass

        self._ensure_card_count(total)

        def _payload_from_row(row: Tuple):
            row_len = len(row)

            ini = row[0] if row_len > 0 else ""
            fim = row[1] if row_len > 1 else ""
            modalidade = row[2] if row_len > 2 else ""
            prof = row[3] if row_len > 3 else ""
            local = row[4] if row_len > 4 else ""
            tag = row[5] if row_len > 5 else ""
            prog_raw = row[6] if row_len > 6 else 0.0
            minsx = row[7] if row_len > 7 else None

            if isinstance(prog_raw, (int, float, str)):
                try:
                    progress_value = float(prog_raw)
                except Exception:
                    progress_value = 0.0
            else:
                progress_value = 0.0

            payload = {
                "inicio": ini,
                "fim": fim,
                "modalidade": modalidade,
                "professor": prof,
                "local": local,
                "tag": (tag or ""),
                "progress": progress_value,
            }

            if self._card_kind == "AGORA":
                payload["mins_left"] = minsx
            else:
                payload["mins_to_start"] = minsx
                payload["progress_upcoming"] = progress_value

            return payload

        for i in range(total):
            payload = _payload_from_row(card_data[i])

            try:
                self.cards_a[i].grid()
                self.cards_a[i].refresh(payload)
            except Exception:
                pass

            try:
                self.cards_b[i].grid()
                self.cards_b[i].refresh(payload)
            except Exception:
                pass

        for i in range(total, len(self.cards_a)):
            try:
                self.cards_a[i].grid_remove()
            except Exception:
                pass
        for i in range(total, len(self.cards_b)):
            try:
                self.cards_b[i].grid_remove()
            except Exception:
                pass

        self._recalc_content_height()

        try:
            self._viewport_h = int(self.scroll_canvas.winfo_height() or self._viewport_h)
        except Exception:
            pass

        self._start_scroll()

    def dispose(self) -> None:
        try:
            self._stop_scroll()
        except Exception:
            pass

        try:
            for cc in (getattr(self, "cards_a", []) + getattr(self, "cards_b", [])):
                try:
                    cc.dispose()
                except Exception:
                    pass
        except Exception:
            pass