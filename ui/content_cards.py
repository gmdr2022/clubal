from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

from ui.theme import MS_CARD_ROTATE


class ClassCard(tk.Frame):
    """
    Card de aula (AGORA / PRÓXIMAS).

    Topo:
    - Título à esquerda
    - Linha central (rotativa): alterna entre "HH:MM — HH:MM"
      e "TERMINA/COMEÇA EM XX MIN."
    - Pill de TAG à direita
    - Barra de progresso embaixo (sem depender do texto).

    O título usa política adaptativa:
    - tenta mostrar modalidade + professor
    - se faltar espaço, prioriza só a modalidade
    - se ainda faltar, aplica elipse na modalidade
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: dict,
        data: dict,
        card_kind: str,  # "AGORA" ou "PROXIMA"
        width: int,
        height: int,
    ) -> None:
        super().__init__(parent, bg=theme["card_bg"], highlightthickness=0)

        self.theme = theme
        self.data = data or {}
        self.card_kind = (card_kind or "").upper().strip()

        # NUNCA use self._w / self._h (Tk usa internamente)
        self._card_w = int(width)
        self._card_h = int(height)

        self.configure(width=self._card_w, height=self._card_h)
        self.grid_propagate(False)
        self.pack_propagate(False)

        # ========= Layout base =========
        self.inner = tk.Frame(self, bg=self.theme["card_bg"])
        self.inner.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.pad_x = int(self.theme.get("card_pad_x", 18))
        self.pad_y = int(self.theme.get("card_pad_y", 6))

        # coluna 0: título (expande)
        # coluna 1: tempo/status (fixo)
        # coluna 2: pill (fixa)
        self.inner.grid_columnconfigure(0, weight=1)
        self.inner.grid_columnconfigure(1, weight=0)
        self.inner.grid_columnconfigure(2, weight=0)

        # ========= Fontes =========
        self.f_title = self.theme.get("f_card_title") or tkfont.Font(
            family="Segoe UI",
            size=18,
            weight="bold",
        )
        self.f_mid = self.theme.get("f_card_mid") or tkfont.Font(
            family="Segoe UI",
            size=14,
            weight="bold",
        )
        self.f_pill = self.theme.get("f_card_pill") or tkfont.Font(
            family="Segoe UI",
            size=11,
            weight="bold",
        )

        # ========= Widgets =========
        self.lbl_title = tk.Label(
            self.inner,
            text="",
            bg=self.theme["card_bg"],
            fg=self.theme["card_fg"],
            font=self.f_title,
            anchor="w",
            justify="left",
        )
        self.lbl_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=(self.pad_x, 12),
            pady=(self.pad_y, 0),
        )

        # label central (vai alternar texto)
        self.lbl_time = tk.Label(
            self.inner,
            text="",
            bg=self.theme["card_bg"],
            fg=self.theme.get("card_time_fg", self.theme["card_fg"]),
            font=self.f_mid,
            anchor="center",
        )
        self.lbl_time.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(0, 18),
            pady=(self.pad_y + 2, 0),
        )

        self.pill = tk.Label(
            self.inner,
            text="",
            bg=self.theme.get("pill_bg_default", "#1F8A5B"),
            fg=self.theme.get("pill_fg", "#06110C"),
            font=self.f_pill,
            width=8,
            anchor="center",
            justify="center",
            padx=14,
            pady=6,
        )
        self.pill.grid(
            row=0,
            column=2,
            sticky="ne",
            padx=(10, self.pad_x),
            pady=(self.pad_y, 0),
        )

        # barra logo abaixo do topo
        self.progress_wrap = tk.Frame(
            self.inner,
            bg=self.theme.get("progress_bg", "#162B40"),
            height=10,
        )
        self.progress_wrap.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=(self.pad_x, self.pad_x),
            pady=(6, 6),
        )
        self.progress_wrap.grid_propagate(False)

        self.progress_fill = tk.Frame(
            self.progress_wrap,
            bg=self.theme.get("progress_fill", "#1F8A5B"),
            width=0,
            height=10,
        )
        self.progress_fill.place(x=0, y=0, relheight=1, width=0)

        # ========= Estado adaptativo do header =========
        self._title_primary = ""
        self._title_professor = ""
        self._title_mode = ""
        self._layout_after = None
        self._last_layout_signature = None

        # ========= Rotação (alternância) =========
        self._rot_after = None
        self._rot_state = 0
        self._rot_ms = MS_CARD_ROTATE
        self._rot_text_a = ""
        self._rot_text_b = ""

        # ========= Pulse (warning) =========
        self._pulse_after = None
        self._pulse_phase = 0.0
        self._pulse_ms = 100
        self._pulse_period_ms = 1600
        self._pulse_active = False
        self._pulse_color_a = None
        self._pulse_color_b = None

        # ========= Estado da barra =========
        self._progress_value = 0.0
        self._progress_kind = self.card_kind or "AGORA"

        self.bind("<Configure>", self._on_layout_changed)
        self.inner.bind("<Configure>", self._on_layout_changed)

        self.refresh(self.data)

    # -----------------------------
    # Helpers
    # -----------------------------
    def _blend_hex(self, a: str, b: str, t: float) -> str:
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

    def _stop_pulse(self) -> None:
        try:
            if self._pulse_after is not None:
                self.after_cancel(self._pulse_after)
        except Exception:
            pass

        self._pulse_after = None
        self._pulse_active = False
        self._pulse_phase = 0.0

    def _tick_pulse(self) -> None:
        try:
            if not self._pulse_active:
                self._stop_pulse()
                return

            a = self._pulse_color_a
            b = self._pulse_color_b
            if not a or not b:
                self._stop_pulse()
                return

            self._pulse_phase += float(self._pulse_ms)
            if self._pulse_phase >= float(self._pulse_period_ms):
                self._pulse_phase -= float(self._pulse_period_ms)

            import math

            x = (self._pulse_phase / float(self._pulse_period_ms)) * (2.0 * math.pi)
            s = (math.sin(x - (math.pi / 2.0)) + 1.0) / 2.0
            t = 0.15 + (s * 0.20)

            col = self._blend_hex(a, b, t)
            self.progress_fill.configure(bg=col)

            self._pulse_after = self.after(int(self._pulse_ms), self._tick_pulse)
        except Exception:
            self._stop_pulse()

    def _safe_str(self, v) -> str:
        if v is None:
            return ""

        try:
            return str(v).strip()
        except Exception:
            return ""

    def _fmt_hhmm(self, v) -> str:
        if v is None:
            return ""

        if hasattr(v, "hour") and hasattr(v, "minute"):
            try:
                return f"{int(v.hour):02d}:{int(v.minute):02d}"
            except Exception:
                pass

        s = self._safe_str(v)
        if not s:
            return ""

        if len(s) >= 5 and s[2] == ":":
            return s[:5]

        return s

    def _extract_title_parts(self, d: dict) -> tuple[str, str]:
        modalidade = self._safe_str(d.get("modalidade"))
        professor = self._safe_str(d.get("professor"))

        if not modalidade:
            modalidade = self._safe_str(d.get("atividade"))
        if not modalidade:
            modalidade = self._safe_str(d.get("local"))

        return (modalidade or "—", professor)

    def _measure_text_px(self, text: str, font: tkfont.Font) -> int:
        try:
            return int(font.measure((text or "").strip()))
        except Exception:
            txt = (text or "").strip()
            try:
                font_size = abs(int(font.cget("size")))
            except Exception:
                font_size = 12
            return int(len(txt) * max(6, font_size))

    def _ellipsize_to_px(self, text: str, max_px: int, font: tkfont.Font) -> str:
        txt = (text or "").strip()
        if not txt:
            return ""

        try:
            limit = int(max_px)
        except Exception:
            limit = 0

        if limit <= 0:
            return ""

        if self._measure_text_px(txt, font) <= limit:
            return txt

        ellipsis = "…"
        if self._measure_text_px(ellipsis, font) > limit:
            return ""

        lo = 0
        hi = len(txt)
        best = ellipsis

        while lo <= hi:
            mid = (lo + hi) // 2
            head = txt[:mid].rstrip()
            candidate = f"{head}{ellipsis}" if head else ellipsis
            if self._measure_text_px(candidate, font) <= limit:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1

        return best

    def _title_variants(self) -> list[tuple[str, str]]:
        primary = (self._title_primary or "").strip()
        professor = (self._title_professor or "").strip()

        variants: list[tuple[str, str]] = []

        if primary and primary != "—" and professor:
            variants.append(("full", f"{primary} • Prof. {professor}"))
            variants.append(("primary_only", primary))
        elif primary and primary != "—":
            variants.append(("primary_only", primary))
        elif professor:
            variants.append(("professor_only", f"Prof. {professor}"))
        else:
            variants.append(("empty", "—"))

        return variants

    def _current_card_width_px(self) -> int:
        widths = []

        for raw in (
            self.winfo_width(),
            self.inner.winfo_width(),
            self._card_w,
        ):
            try:
                v = int(raw)
            except Exception:
                v = 0
            if v > 0:
                widths.append(v)

        try:
            cfg_w = int(self.cget("width"))
        except Exception:
            cfg_w = 0
        if cfg_w > 0:
            widths.append(cfg_w)

        return max(widths) if widths else 0

    def _compute_title_slot_px(self) -> int:
        card_w = self._current_card_width_px()

        time_text = self._safe_str(self.lbl_time.cget("text"))

        # Importante:
        # não usar a largura atual renderizada do widget como referência principal,
        # porque ela pode "segurar" a largura maior do estado anterior da rotação.
        # Aqui a reserva deve seguir o conteúdo ATIVO do momento.
        time_text_w = self._measure_text_px(time_text, self.f_mid)

        # Piso visual para o bloco central não ficar apertado demais.
        time_slot_w = max(110, time_text_w + 8)

        # Para a pill, manter uma reserva estável é desejável.
        pill_w = max(
            int(self.pill.winfo_reqwidth() or 0),
            self._measure_text_px(self._safe_str(self.pill.cget("text")), self.f_pill) + 28,
            96,
        )

        reserved = (
            self.pad_x
            + 12
            + time_slot_w
            + 18
            + 10
            + pill_w
            + self.pad_x
            + 8
        )

        return max(48, int(card_w - reserved))

    def _select_title_text(self, max_px: int) -> tuple[str, str]:
        variants = self._title_variants()

        for mode, text in variants:
            if self._measure_text_px(text, self.f_title) <= max_px:
                return mode, text

        primary = (self._title_primary or "").strip()
        professor = (self._title_professor or "").strip()

        if primary and primary != "—":
            ell = self._ellipsize_to_px(primary, max_px, self.f_title)
            if ell:
                return "primary_ellipsis", ell

        if professor and (not primary or primary == "—"):
            prof_text = f"Prof. {professor}"
            ell = self._ellipsize_to_px(prof_text, max_px, self.f_title)
            if ell:
                return "professor_ellipsis", ell

        dash = self._ellipsize_to_px("—", max_px, self.f_title)
        return "empty", (dash or "")

    def _apply_title_layout(self) -> None:
        try:
            slot_px = self._compute_title_slot_px()
            mode, text = self._select_title_text(slot_px)
            signature = (
                slot_px,
                self._safe_str(self.lbl_time.cget("text")),
                self._safe_str(self.pill.cget("text")),
                mode,
                text,
            )
            if signature == self._last_layout_signature:
                return

            self._title_mode = mode
            self.lbl_title.configure(text=text)
            self._last_layout_signature = signature
        except Exception:
            try:
                fallback = self._title_variants()[0][1]
            except Exception:
                fallback = "—"
            self.lbl_title.configure(text=fallback)
            self._title_mode = "fallback"
            self._last_layout_signature = None

    def _cancel_layout_refresh(self) -> None:
        try:
            if self._layout_after is not None:
                self.after_cancel(self._layout_after)
        except Exception:
            pass
        self._layout_after = None

    def _flush_layout_refresh(self) -> None:
        self._layout_after = None
        self._apply_title_layout()

    def _schedule_layout_refresh(self) -> None:
        if self._layout_after is not None:
            return

        try:
            self._layout_after = self.after_idle(self._flush_layout_refresh)
        except Exception:
            self._flush_layout_refresh()

    def _on_layout_changed(self, _evt=None) -> None:
        try:
            w = int(self.winfo_width() or 0)
            h = int(self.winfo_height() or 0)
            if w > 1:
                self._card_w = w
            if h > 1:
                self._card_h = h
        except Exception:
            pass

        self._refresh_progress_width()
        self._schedule_layout_refresh()

    def _pill_colors_for_tag(self, tag: str) -> tuple[str, str]:
        t = (tag or "").upper().strip()

        if t == "MENOR":
            return (
                self.theme.get("pill_bg_menor", "#C6A600"),
                self.theme.get("pill_fg_menor", "#0B0B0B"),
            )

        if t == "GERAL":
            return (
                self.theme.get("pill_bg_geral", "#1F8A5B"),
                self.theme.get("pill_fg_geral", "#06110C"),
            )

        return (
            self.theme.get("pill_bg_default", "#1F8A5B"),
            self.theme.get("pill_fg", "#06110C"),
        )

    def _apply_time_text(self, s: str) -> None:
        try:
            self.lbl_time.configure(text=(s or "").strip())
        except Exception:
            pass

        self._schedule_layout_refresh()

    def _stop_rotation(self) -> None:
        try:
            if self._rot_after is not None:
                self.after_cancel(self._rot_after)
        except Exception:
            pass

        self._rot_after = None

    def _tick_rotation(self) -> None:
        try:
            if not (self._rot_text_a and self._rot_text_b):
                self._stop_rotation()
                return

            self._rot_state = 1 - int(self._rot_state)

            if self._rot_state == 0:
                self._apply_time_text(self._rot_text_a)
            else:
                self._apply_time_text(self._rot_text_b)

            self._rot_after = self.after(int(self._rot_ms), self._tick_rotation)
        except Exception:
            self._stop_rotation()

    def _start_rotation(self) -> None:
        self._stop_rotation()
        self._rot_after = self.after(int(self._rot_ms), self._tick_rotation)

    def _refresh_progress_width(self) -> None:
        try:
            p = float(self._progress_value)
        except Exception:
            p = 0.0

        if p < 0.0:
            p = 0.0
        if p > 1.0:
            p = 1.0

        w = max(1, int(self.progress_wrap.winfo_width() or 0))
        if w <= 1:
            w = max(1, int(self._current_card_width_px()) - (self.pad_x * 2))

        fill_w = int(w * p)
        self.progress_fill.place_configure(width=fill_w)

    # -----------------------------
    # API pública
    # -----------------------------
    def refresh(self, data: dict) -> None:
        self.data = data or {}
        self._last_layout_signature = None

        if self.card_kind != "AGORA":
            self._stop_pulse()

        self._title_primary, self._title_professor = self._extract_title_parts(self.data)

        ini = self._fmt_hhmm(self.data.get("inicio"))
        fim = self._fmt_hhmm(self.data.get("fim"))

        if ini and fim:
            base_time = f"{ini} — {fim}"
        elif ini:
            base_time = ini
        elif fim:
            base_time = fim
        else:
            base_time = ""

        extra = ""
        if self.card_kind == "AGORA":
            mins_left = self.data.get("mins_left")
            try:
                m = int(mins_left) if mins_left is not None else None
            except Exception:
                m = None

            if m is not None:
                extra = f"TERMINA EM {m} MIN."
        else:
            mins_to_start = self.data.get("mins_to_start")
            try:
                m = int(mins_to_start) if mins_to_start is not None else None
            except Exception:
                m = None

            if m is not None:
                extra = f"COMEÇA EM {m} MIN."

        if base_time and extra:
            self._rot_text_a = base_time
            self._rot_text_b = extra
            self._rot_state = 0
            self._apply_time_text(self._rot_text_a)
            self._start_rotation()
        else:
            self._rot_text_a = ""
            self._rot_text_b = ""
            self._stop_rotation()
            self._apply_time_text(base_time or extra or "")

        tag = self._safe_str(self.data.get("tag"))
        pill_bg, pill_fg = self._pill_colors_for_tag(tag)
        self.pill.configure(
            text=(tag.upper() if tag else "—"),
            bg=pill_bg,
            fg=pill_fg,
        )

        if self.card_kind == "AGORA":
            prog = self.data.get("progress")
            if isinstance(prog, (int, float, str)):
                try:
                    p = float(prog)
                except Exception:
                    p = 0.0
            else:
                p = 0.0

            self._set_progress(p, kind="AGORA")
        else:
            prog_upcoming = self.data.get("progress_upcoming", 1.0)
            if isinstance(prog_upcoming, (int, float, str)):
                try:
                    p_upcoming = float(prog_upcoming)
                except Exception:
                    p_upcoming = 1.0
            else:
                p_upcoming = 1.0

            self._set_progress(p_upcoming, kind="PROXIMA")

        self._apply_title_layout()
        self._schedule_layout_refresh()

    def _set_progress(self, progress: float, kind: str) -> None:
        try:
            p = float(progress)
        except Exception:
            p = 0.0

        if p < 0.0:
            p = 0.0
        if p > 1.0:
            p = 1.0

        self._progress_value = p
        self._progress_kind = (kind or self.card_kind or "AGORA").upper().strip()

        if self._progress_kind == "PROXIMA":
            self._stop_pulse()
            self.progress_fill.configure(
                bg=self.theme.get("progress_fill_upcoming", "#2B79D6")
            )
        else:
            c_blue = self.theme.get("progress_fill_upcoming", "#2B79D6")
            c_green = self.theme.get("progress_fill", "#1F8A5B")
            c_orange = self.theme.get("progress_fill_warn", "#F5A000")
            c_red = self.theme.get("progress_fill_crit", "#E34850")

            if p >= 0.75:
                self._stop_pulse()
                fill_col = c_blue
            elif p >= 0.45:
                self._stop_pulse()
                fill_col = c_green
            elif p >= 0.20:
                self._stop_pulse()
                fill_col = c_orange
            else:
                fill_col = c_red
                self._pulse_color_a = c_red
                self._pulse_color_b = c_orange

                if not self._pulse_active:
                    self._pulse_active = True
                    self._pulse_phase = 0.0
                    self.progress_fill.configure(bg=fill_col)
                    self._pulse_after = self.after(int(self._pulse_ms), self._tick_pulse)

            if not self._pulse_active:
                self.progress_fill.configure(bg=fill_col)

        self._refresh_progress_width()

    def dispose(self) -> None:
        try:
            self._stop_rotation()
        except Exception:
            pass

        try:
            self._stop_pulse()
        except Exception:
            pass

        try:
            self._cancel_layout_refresh()
        except Exception:
            pass