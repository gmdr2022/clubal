from __future__ import annotations

from typing import Tuple

import tkinter as tk


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

    card._tmarquee_label1 = tk.Label(
        card._tmarquee_frame,
        text="",
        font=card._f_title_status,
        fg="#bcd3ff",
        bg=bg,
        bd=0,
        highlightthickness=0
    )
    card._tmarquee_label1.place(x=0, y=0)

    card._tmarquee_label2 = tk.Label(
        card._tmarquee_frame,
        text="",
        font=card._f_title_status,
        fg="#bcd3ff",
        bg=bg,
        bd=0,
        highlightthickness=0
    )
    card._tmarquee_label2.place(x=0, y=0)


def layout_top_status_right(card, box: Tuple[int, int, int, int], text: str, bg: str) -> None:
    """
    box: (x1,y1,x2,y2) área do status (direita). Deve ser CLIP real.
    - Se couber: mostra estático alinhado à direita.
    - Se não couber: marquee contínuo rolando para a esquerda.
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
    except Exception:
        return

    safe_text = (" ".join((text or "").split()) or "—").upper()

    try:
        top_label1.configure(text=safe_text, font=card._f_title_status, bg=bg)
        top_label2.configure(text=safe_text, font=card._f_title_status, bg=bg)
    except Exception:
        return

    try:
        text_w = int(card._f_title_status.measure(safe_text))
    except Exception:
        text_w = len(safe_text) * 9

    try:
        line_h = int(card._f_title_status.metrics("linespace"))
    except Exception:
        line_h = 18

    y_center = int(max(0, (h - line_h) // 2))
    card._tmarquee_last_box = box

    if text_w <= (w - 6):
        stop_top_marquee(card)

        x_right = int(max(0, w - text_w))
        try:
            top_label1.place_configure(x=x_right, y=y_center)
            top_label2.place_configure(x=w + 2000, y=y_center)
        except Exception:
            pass
        return

    stop_top_marquee(card)
    card._tmarquee_running = True

    spacing = int(max(40, min(int(card._tmarquee_gap_px), max(40, w // 2))))

    card._tmarquee_x1 = int(w + 2)
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