from __future__ import annotations

import tkinter as tk


class RoundedFrame(tk.Canvas):
    """
    Canvas com retângulo arredondado + sombra leve (apenas estética).
    Suporta "gloss" opcional.
    Também normaliza shadow_stipple para evitar erro do Tk (ex.: "gray10").
    """

    _VALID_STIPPLES = ("gray12", "gray25", "gray50", "gray75", "")

    def __init__(
        self,
        master,
        radius=16,
        bg="#ffffff",
        border="#d0d7e2",
        shadow=False,
        shadow_offset=(3, 4),
        shadow_stipple="gray25",
        gloss: bool = False,
        gloss_inset: int = 3,
        **kwargs
    ):
        super().__init__(master, highlightthickness=0, bd=0, bg=master["bg"], **kwargs)
        self.radius = radius
        self.fill = bg
        self.border = border
        self.shadow = shadow
        self.shadow_offset = shadow_offset

        self.shadow_stipple = self._normalize_stipple(shadow_stipple)

        self.gloss = bool(gloss)
        self.gloss_inset = int(gloss_inset)

        self.bind("<Configure>", self._redraw)

    def _normalize_stipple(self, s: str) -> str:
        """
        Tk aceita bitmaps específicos para stipple. Alguns valores (ex.: "gray10")
        não existem. Aqui fazemos fallback seguro.
        """
        try:
            v = str(s or "").strip()
            if not v:
                return ""

            v_low = v.lower()

            if v_low == "gray10":
                return "gray12"

            if v_low in self._VALID_STIPPLES:
                return v_low

            if v_low.startswith("gray"):
                try:
                    n = int("".join([c for c in v_low if c.isdigit()]) or "0")
                except Exception:
                    n = 0

                choices = [12, 25, 50, 75]
                closest = min(choices, key=lambda x: abs(x - n))
                return f"gray{closest}"

            return "gray25"
        except Exception:
            return "gray25"

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

    def _redraw(self, _evt=None):
        self.delete("all")

        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 2 or h <= 2:
            return

        r = min(self.radius, w // 2, h // 2)
        x1, y1, x2, y2 = 1, 1, w - 2, h - 2

        if self.shadow:
            dx, dy = self.shadow_offset
            self._round_rect(
                x1 + dx,
                y1 + dy,
                x2 + dx,
                y2 + dy,
                r,
                fill="#000000",
                outline="#000000",
                tags=("shadow",),
            )

            if self.shadow_stipple:
                self.itemconfig("shadow", stipple=self.shadow_stipple)

        self._round_rect(
            x1,
            y1,
            x2,
            y2,
            r,
            fill=self.fill,
            outline=self.border,
            tags=("main",),
        )

        if self.gloss:
            inset = max(1, int(self.gloss_inset))
            gx1 = x1 + inset
            gy1 = y1 + inset
            gx2 = x2 - inset
            gy2 = y2 - inset

            if gx2 > gx1 + 6 and gy2 > gy1 + 6:
                top_hi = self._blend_hex(self.fill, "#ffffff", 0.22)
                top_hi2 = self._blend_hex(self.fill, "#ffffff", 0.12)
                bot_lo = self._blend_hex(self.fill, "#000000", 0.30)
                bot_lo2 = self._blend_hex(self.fill, "#000000", 0.18)

                self.create_line(gx1 + 10, gy1 + 2, gx2 - 10, gy1 + 2, fill=top_hi, width=1)
                self.create_line(gx1 + 10, gy1 + 3, gx2 - 10, gy1 + 3, fill=top_hi2, width=1)

                self.create_line(gx1 + 10, gy2 - 3, gx2 - 10, gy2 - 3, fill=bot_lo2, width=1)
                self.create_line(gx1 + 10, gy2 - 2, gx2 - 10, gy2 - 2, fill=bot_lo, width=1)

                inner = self._blend_hex(self.border, "#ffffff", 0.18)
                self._round_rect(
                    gx1,
                    gy1,
                    gx2,
                    gy2,
                    max(10, r - inset),
                    fill="",
                    outline=inner,
                    tags=("gloss",),
                )

    def _round_rect(self, x1, y1, x2, y2, r, fill, outline, tags=()):
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=outline, tags=tags)