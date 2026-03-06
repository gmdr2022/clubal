from __future__ import annotations

from typing import Tuple

import tkinter as tk
import tkinter.font as tkfont


def stop_top_marquee(card) -> None:
    try:
        if card._tmarquee_after is not None:
            card.after_cancel(card._tmarquee_after)
    except Exception:
        pass
    card._tmarquee_after = None
    card._tmarquee_running = False


def ensure_top_marquee_widgets(card, bg: str) -> None:
    if card._tmarquee_frame is not None and card._tmarquee_label1 is not None and card._tmarquee_label2 is not None:
        return

    card._tmarquee_frame = tk.Frame(card.canvas, bg=bg, bd=0, highlightthickness=0)

    # Dedicated font for the TOP status (so we can resize without affecting other labels).
    try:
        base_actual = card._f_title_status.actual()
        card._tmarquee_font = tkfont.Font(
            family=base_actual.get("family", "Segoe UI"),
            size=int(base_actual.get("size", 14)),
            weight=base_actual.get("weight", "bold"),
            slant=base_actual.get("slant", "roman"),
            underline=int(base_actual.get("underline", 0)),
            overstrike=int(base_actual.get("overstrike", 0)),
        )
    except Exception:
        card._tmarquee_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")

    try:
        s0 = int(card._tmarquee_font.cget("size"))
    except Exception:
        s0 = 14

    card._tmarquee_font_sign = -1 if s0 < 0 else 1
    card._tmarquee_font_base_abs = abs(int(s0)) if int(s0) != 0 else 14
    card._tmarquee_font_min_abs = max(12, int(round(card._tmarquee_font_base_abs * 0.78)))
    card._tmarquee_fit_key = None
    card._tmarquee_fit_abs = card._tmarquee_font_base_abs

    card._tmarquee_label1 = tk.Label(
        card._tmarquee_frame,
        text="",
        font=card._tmarquee_font,
        fg="#bcd3ff",
        bg=bg,
        bd=0,
        highlightthickness=0,
        padx=0,
        pady=0,
    )
    card._tmarquee_label1.place(x=0, y=0)

    card._tmarquee_label2 = tk.Label(
        card._tmarquee_frame,
        text="",
        font=card._tmarquee_font,
        fg="#bcd3ff",
        bg=bg,
        bd=0,
        highlightthickness=0,
        padx=0,
        pady=0,
    )
    card._tmarquee_label2.place(x=0, y=0)


def layout_top_status_right(card, box: Tuple[int, int, int, int], text: str, bg: str) -> None:
    """
    TOP right status:
    1) Try to fit by shrinking font down to a safe minimum (TV-friendly).
    2) If still doesn't fit, run marquee (right-to-left).
    """
    x1, y1, x2, y2 = box
    w = max(10, int(x2 - x1))
    h = max(10, int(y2 - y1))

    ensure_top_marquee_widgets(card, bg=bg)

    if card._tmarquee_frame is None or card._tmarquee_label1 is None or card._tmarquee_label2 is None:
        return

    top_label1 = card._tmarquee_label1
    top_label2 = card._tmarquee_label2

    try:
        if card._tmarquee_win_id is None:
            card._tmarquee_win_id = card.canvas.create_window(
                x1, y1, anchor="nw",
                window=card._tmarquee_frame,
                width=w,
                height=h
            )
        else:
            card.canvas.coords(card._tmarquee_win_id, x1, y1)
            card.canvas.itemconfig(card._tmarquee_win_id, width=w, height=h)

        # Keep the frame sized to the clip box (prevents odd clipping on small screens)
        try:
            card._tmarquee_frame.configure(width=w, height=h)
        except Exception:
            pass

        # Ensure it's above later draw calls
        try:
            card.canvas.tag_raise(card._tmarquee_win_id)
        except Exception:
            pass
    except Exception:
        return

    safe_text = (" ".join((text or "").split()) or "—").upper()

    # Apply bg and text
    try:
        top_label1.configure(text=safe_text, bg=bg)
        top_label2.configure(text=safe_text, bg=bg)
    except Exception:
        return

    # Decide font size (shrink-to-fit up to a minimum)
    try:
        font_obj = card._tmarquee_font
    except Exception:
        font_obj = card._f_title_status

    try:
        sign = int(getattr(card, "_tmarquee_font_sign", -1 if int(font_obj.cget("size")) < 0 else 1))
        base_abs = int(getattr(card, "_tmarquee_font_base_abs", abs(int(font_obj.cget("size"))) or 14))
        min_abs = int(getattr(card, "_tmarquee_font_min_abs", max(12, int(round(base_abs * 0.78)))))
    except Exception:
        sign = 1
        base_abs = 14
        min_abs = 12

    fit_key = (safe_text, w, h, base_abs, min_abs, sign)
    if getattr(card, "_tmarquee_fit_key", None) != fit_key:
        fit_abs = base_abs
        avail_w = int(max(10, w - 6))

        # Try from base -> min
        for abs_s in range(base_abs, min_abs - 1, -1):
            try:
                font_obj.configure(size=int(sign * abs_s))
                tw = int(font_obj.measure(safe_text))
            except Exception:
                tw = len(safe_text) * 9

            if tw <= avail_w:
                fit_abs = abs_s
                break
            fit_abs = abs_s

        card._tmarquee_fit_key = fit_key
        card._tmarquee_fit_abs = fit_abs

    try:
        fit_abs = int(getattr(card, "_tmarquee_fit_abs", base_abs))
        font_obj.configure(size=int(sign * fit_abs))
    except Exception:
        pass

    # Measure with final font choice
    try:
        text_w = int(font_obj.measure(safe_text))
    except Exception:
        text_w = len(safe_text) * 9

    # Vertical center using REAL requested height
    try:
        card._tmarquee_frame.update_idletasks()
        req_h = int(max(1, top_label1.winfo_reqheight()))
    except Exception:
        req_h = 0

    try:
        line_h = int(font_obj.metrics("linespace"))
    except Exception:
        line_h = 18

    if req_h <= 0:
        req_h = line_h
    else:
        req_h = max(req_h, line_h)

    y_center = int(max(0, (h - req_h) // 2))
    card._tmarquee_last_box = box

    # If it fits after shrink -> static right-aligned
    if text_w <= (w - 6):
        stop_top_marquee(card)
        x_center = int(max(0, (w - text_w) // 2))
        try:
            top_label1.place_configure(x=x_center, y=y_center)
            top_label2.place_configure(x=w + 2000, y=y_center)
        except Exception:
            pass
        return

    # If it still doesn't fit -> marquee
    stop_top_marquee(card)
    card._tmarquee_running = True

    spacing = int(max(40, min(int(card._tmarquee_gap_px), max(40, w // 2))))

    # Start visible (avoids "it disappeared" on small screens)
    card._tmarquee_x1 = 2
    card._tmarquee_x2 = int(card._tmarquee_x1 + text_w + spacing)

    try:
        top_label1.place_configure(x=card._tmarquee_x1, y=y_center)
        top_label2.place_configure(x=card._tmarquee_x2, y=y_center)
    except Exception:
        pass

    def _tick():
        if not card._tmarquee_running:
            return
        if card._tmarquee_last_box != box:
            return

        step = int(max(1, card._tmarquee_speed_px))

        card._tmarquee_x1 -= step
        card._tmarquee_x2 -= step

        if (card._tmarquee_x1 + text_w) < -2:
            card._tmarquee_x1 = int(card._tmarquee_x2 + text_w + spacing)
        if (card._tmarquee_x2 + text_w) < -2:
            card._tmarquee_x2 = int(card._tmarquee_x1 + text_w + spacing)

        try:
            top_label1.place_configure(x=card._tmarquee_x1)
            top_label2.place_configure(x=card._tmarquee_x2)
        except Exception:
            pass

        card._tmarquee_after = card.after(int(card._tmarquee_tick_ms), _tick)

    card._tmarquee_after = card.after(int(card._tmarquee_tick_ms), _tick)


def stop_forecast_marquee(card) -> None:
    try:
        if card._marquee_after is not None:
            card.after_cancel(card._marquee_after)
    except Exception:
        pass
    card._marquee_after = None
    card._marquee_running = False


def ensure_forecast_marquee_widgets(card) -> None:
    if card._forecast_frame is not None and card._forecast_label is not None and card._forecast_label2 is not None:
        return

    bg = getattr(card, "_forecast_strip_bg", card.glass_fill)
    edge = getattr(card, "_forecast_strip_edge", card.glass_edge)

    card._forecast_frame = tk.Frame(card.canvas, bg=bg, bd=0, highlightthickness=1, highlightbackground=edge)
    card._forecast_label = tk.Label(
        card._forecast_frame,
        text="",
        font=card._f_forecast,
        fg="#ffffff",
        bg=bg,
        bd=0,
        highlightthickness=0
    )
    card._forecast_label.place(x=0, y=0)

    card._forecast_label2 = tk.Label(
        card._forecast_frame,
        text="",
        font=card._f_forecast,
        fg="#ffffff",
        bg=bg,
        bd=0,
        highlightthickness=0
    )
    card._forecast_label2.place(x=0, y=0)

def start_or_layout_forecast_marquee(card, box: Tuple[int, int, int, int], text: str) -> None:
    x1, y1, x2, y2 = box
    w = max(10, int(x2 - x1))
    h = max(10, int(y2 - y1))

    ensure_forecast_marquee_widgets(card)

    if card._forecast_frame is None or card._forecast_label is None or card._forecast_label2 is None:
        return

    forecast_label1 = card._forecast_label
    forecast_label2 = card._forecast_label2

    try:
        if card._forecast_win_id is None:
            card._forecast_win_id = card.canvas.create_window(
                x1, y1, anchor="nw",
                window=card._forecast_frame,
                width=w,
                height=h
            )
        else:
            card.canvas.coords(card._forecast_win_id, x1, y1)
            card.canvas.itemconfig(card._forecast_win_id, width=w, height=h)

        # garante que o widget ocupe o tamanho do box (evita clipping em telas menores)
        card._forecast_frame.configure(width=w, height=h)

        # garante que o forecast fique por cima de draws posteriores
        card.canvas.tag_raise(card._forecast_win_id)
    except Exception:
        return

    safe_text = " ".join((text or "").split()) or "—"

    try:
        forecast_label1.configure(text=safe_text, font=card._f_forecast, padx=0, pady=0)
        forecast_label2.configure(text=safe_text, font=card._f_forecast, padx=0, pady=0)
    except Exception:
        return

    try:
        text_w = int(card._f_forecast.measure(safe_text))
    except Exception:
        text_w = len(safe_text) * 10

    # altura REAL do label (mais confiável que linespace em telas menores)
    try:
        card._forecast_frame.update_idletasks()
        req_h = int(max(1, forecast_label1.winfo_reqheight()))
    except Exception:
        req_h = 0

    try:
        line_h = int(card._f_forecast.metrics("linespace"))
    except Exception:
        line_h = 26

    if req_h <= 0:
        req_h = line_h
    else:
        req_h = max(req_h, line_h)

    y_center = int(max(0, (h - req_h) // 2))

    card._marquee_last_box = box

    if text_w <= (w - 10):
        stop_forecast_marquee(card)
        x_center = int(max(0, (w - text_w) // 2))
        try:
            forecast_label1.place_configure(x=x_center, y=y_center)
            forecast_label2.place_configure(x=w + 2000, y=y_center)
        except Exception:
            pass
        return

    stop_forecast_marquee(card)
    card._marquee_running = True

    spacing = int(max(40, min(int(card._marquee_gap_px), max(40, w // 2))))

    # começa visível (evita faixa vazia)
    card._marquee_x = 2
    card._marquee_x2 = int(card._marquee_x + text_w + spacing)

    try:
        forecast_label1.place_configure(x=card._marquee_x, y=y_center)
        forecast_label2.place_configure(x=card._marquee_x2, y=y_center)
    except Exception:
        pass

    def _tick():
        if not card._marquee_running:
            return
        if card._marquee_last_box != box:
            return

        step = int(max(1, card._marquee_speed_px))

        card._marquee_x -= step
        card._marquee_x2 -= step

        if (card._marquee_x + text_w) < -2:
            card._marquee_x = int(card._marquee_x2 + text_w + spacing)
        if (card._marquee_x2 + text_w) < -2:
            card._marquee_x2 = int(card._marquee_x + text_w + spacing)

        try:
            forecast_label1.place_configure(x=card._marquee_x)
            forecast_label2.place_configure(x=card._marquee_x2)
        except Exception:
            pass

        card._marquee_after = card.after(int(card._marquee_tick_ms), _tick)

    card._marquee_after = card.after(int(card._marquee_tick_ms), _tick)

__all__ = [
    "ensure_forecast_marquee_widgets",
    "ensure_top_marquee_widgets",
    "layout_top_status_right",
    "start_or_layout_forecast_marquee",
    "stop_forecast_marquee",
    "stop_top_marquee",
]