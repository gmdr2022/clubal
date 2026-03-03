from __future__ import annotations

from typing import Callable, Optional

import tkinter as tk
import tkinter.font as tkfont

from ui.theme import (
    SP_8,
    SP_12,
    SP_16,
    RADIUS_SM,
    RADIUS_MD,
    SHADOW_SOFT,
)
from ui.rounded_frame import RoundedFrame
from ui.content_cards import ClassCard
from ui.content_sections import SectionFrame
from ui.header_hours import HoursCard
from ui.header_weather import WeatherCard


def build_main_ui(app, logger: Optional[Callable[[str], None]] = None) -> None:
    # cleanup explícito (evita after() pendurado em rebuild de tema)
    try:
        if hasattr(app, "agora") and app.agora is not None:
            try:
                app.agora.dispose()
            except Exception:
                pass
        if hasattr(app, "hours_card") and app.hours_card is not None:
            try:
                app.hours_card.dispose()
            except Exception:
                pass
        if hasattr(app, "prox") and app.prox is not None:
            try:
                app.prox.dispose()
            except Exception:
                pass
        if hasattr(app, "weather_card") and app.weather_card is not None:
            try:
                app.weather_card.dispose()
            except Exception:
                pass
    except Exception:
        pass

    for w in list(app.winfo_children()):
        try:
            w.destroy()
        except Exception:
            pass

    hours_w, weather_w, card_h, header_h = app._calc_header_geometry()
    right_w = int(hours_w + 40 + weather_w) + 24
    app._last_header_geom = (hours_w, weather_w, card_h, header_h)

    app.header = tk.Frame(app, bg=app.bg_header, height=header_h)
    app.header.pack(fill="x", side="top")
    app.header.pack_propagate(False)

    # -------------------------
    # Header background
    # -------------------------
    if app.is_day_theme:
        header_base = app.bg_header
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

    app.header_bg = tk.Frame(app.header, bg=header_base)
    app.header_bg.place(x=0, y=0, relwidth=1, relheight=1)

    app.header_panel = tk.Frame(app.header, bg=panel_fill)
    app.header_panel.place(
        x=inset,
        y=inset,
        relwidth=1,
        width=-(2 * inset),
        relheight=1,
        height=-(2 * inset),
    )

    app.header_panel_edge = tk.Frame(app.header_panel, bg=panel_edge)
    app.header_panel_top_glow = tk.Frame(app.header_panel, bg="#1b4f91", height=1)
    app.header_panel_top_glow.place(x=0, y=1, relwidth=1)
    app.header_panel_edge.place(x=0, y=0, relwidth=1, height=1)

    app.header_panel_edge2 = tk.Frame(app.header_panel, bg=panel_edge)
    app.header_panel_edge2.place(x=0, y=0, width=1, relheight=1)

    app.header_panel_edge3 = tk.Frame(app.header_panel, bg=panel_edge)
    app.header_panel_edge3.place(relx=1.0, x=-1, y=0, width=1, relheight=1)

    app.header_panel_edge4 = tk.Frame(app.header_panel, bg=panel_edge)
    app.header_panel_edge4.place(x=0, rely=1.0, y=-1, relwidth=1, height=1)

    app.header_bottom_line = tk.Frame(app.header_panel, bg=panel_bottom, height=3)
    app.header_bottom_line.pack(side="bottom", fill="x")

    app.header_bg.lower()
    app.header_panel.lower()

    header_fill = panel_fill

    # HEADER GRID (2 linhas)
    app.header.grid_rowconfigure(0, weight=1)
    app.header.grid_rowconfigure(1, weight=1)

    app.header.grid_columnconfigure(0, weight=1)
    app.header.grid_columnconfigure(1, weight=0, minsize=right_w)

    # LEFT STACK
    app.left_stack = tk.Frame(app.header, bg=header_fill)
    app.left_stack.grid(
        row=0,
        column=0,
        rowspan=2,
        sticky="nsew",
        padx=(SP_12, SP_8),
        pady=(SP_8, SP_12),
    )
    app.left_stack.grid_columnconfigure(0, weight=1)
    app.left_stack.grid_rowconfigure(0, weight=0)
    app.left_stack.grid_rowconfigure(1, weight=0)
    app.left_stack.grid_rowconfigure(2, weight=1)

    # Row 0: logos
    LOGOS_ROW_H = 150
    CLUBAL_SLOT_S = LOGOS_ROW_H

    app.logos_row = tk.Frame(app.left_stack, bg=header_fill, height=LOGOS_ROW_H)
    app.logos_row.grid(row=0, column=0, sticky="ew")
    app.logos_row.grid_propagate(False)

    app.logos_row.grid_columnconfigure(0, weight=0, minsize=CLUBAL_SLOT_S)
    app.logos_row.grid_columnconfigure(1, weight=1, minsize=160)

    app.clubal_slot = tk.Frame(
        app.logos_row,
        bg=header_fill,
        width=CLUBAL_SLOT_S,
        height=LOGOS_ROW_H,
    )
    app.clubal_slot.grid(row=0, column=0, sticky="w")
    app.clubal_slot.grid_propagate(False)

    app.logo_img = None
    app.logo_lbl = tk.Label(app.clubal_slot, bg=header_fill)
    app.logo_lbl.place(relx=0.5, rely=0.5, anchor="center")

    app.client_slot = tk.Frame(app.logos_row, bg=header_fill, height=LOGOS_ROW_H)
    app.client_slot.grid(row=0, column=1, sticky="ew", padx=(18, 0))
    app.client_slot.grid_propagate(False)

    app.client_logo_img = None
    app.client_logo_lbl = tk.Label(app.client_slot, bg=header_fill)
    app.client_logo_lbl.place(relx=0.5, rely=0.5, anchor="center")

    if app.DEBUG_LAYOUT:
        app.clubal_slot.configure(highlightthickness=2, highlightbackground="#00ff00")
        app.client_slot.configure(highlightthickness=2, highlightbackground="#00ffff")

    app._refresh_logo()
    app._refresh_client_logo()

    # Row 1: DateCard
    app.datecard = tk.Frame(app.left_stack, bg=header_fill)
    app.datecard.grid(row=1, column=0, sticky="ew", pady=(10, 8))

    if app.DEBUG_LAYOUT:
        app.datecard.configure(highlightthickness=2, highlightbackground="#ffd000")

    app._datecard_h = 58

    if app.is_day_theme:
        datecard_bg = app._blend_hex(panel_fill, "#ffffff", 0.10)
        datecard_border = app._blend_hex(panel_fill, "#ffffff", 0.20)
        datecard_fg = "#ffffff"
        shadow_stipple = "gray12"
    else:
        datecard_bg = app._blend_hex("#0b223c", "#ffffff", 0.06)
        datecard_border = app._blend_hex("#132744", "#ffffff", 0.08)
        datecard_fg = "#eaf2ff"
        shadow_stipple = "gray12"

    app.datecard_canvas = RoundedFrame(
        app.datecard,
        radius=RADIUS_SM,
        bg=datecard_bg,
        border=datecard_border,
        shadow=True,
        shadow_offset=(2, 3),
        shadow_stipple=shadow_stipple,
        gloss=True,
        gloss_inset=3,
        height=app._datecard_h,
    )
    app.datecard_canvas.pack(fill="x", expand=False)
    app.datecard_canvas.pack_propagate(False)

    app.f_date_line = tkfont.Font(
        family="Segoe UI",
        size=18,
        weight="bold",
    )

    app._date_text_id = None
    app._date_shadow_id = None

    def _draw_date_text(_evt=None):
        try:
            w = app.datecard_canvas.winfo_width()
            h = app.datecard_canvas.winfo_height()
            if w <= 10 or h <= 10:
                return

            if app._date_text_id is None:
                app._date_shadow_id = app.datecard_canvas.create_text(
                    (w // 2) + 1,
                    (h // 2) + 1,
                    anchor="center",
                    text="",
                    fill="#061a33" if app.is_day_theme else "#000000",
                    font=app.f_date_line,
                )
                app._date_text_id = app.datecard_canvas.create_text(
                    w // 2,
                    h // 2,
                    anchor="center",
                    text="",
                    fill=datecard_fg,
                    font=app.f_date_line,
                )
            else:
                shadow_id = app._date_shadow_id
                text_id = app._date_text_id

                if shadow_id is not None:
                    app.datecard_canvas.coords(shadow_id, (w // 2) + 1, (h // 2) + 1)
                if text_id is not None:
                    app.datecard_canvas.coords(text_id, w // 2, h // 2)

        except Exception:
            pass

    app.datecard_canvas.bind("<Configure>", _draw_date_text)
    app.after(0, _draw_date_text)

    # Row 2: clock
    app.clockbox = tk.Frame(app.left_stack, bg=header_fill)
    app.clockbox.grid(row=2, column=0, sticky="nsew")

    if app.DEBUG_LAYOUT:
        app.clockbox.configure(highlightthickness=2, highlightbackground="#ff0000")

    mono_family = "Cascadia Mono"
    try:
        app.f_time_main = tkfont.Font(family=mono_family, size=34, weight="bold")
    except Exception:
        app.f_time_main = tkfont.Font(family="Consolas", size=34, weight="bold")

    try:
        app.f_time_sec = tkfont.Font(family=mono_family, size=22, weight="bold")
    except Exception:
        app.f_time_sec = tkfont.Font(family="Consolas", size=22, weight="bold")

    if app.is_day_theme:
        app.header_onpanel_main = "#ffffff"
        app.header_onpanel_soft = "#bcd3ff"
    else:
        app.header_onpanel_main = "#eaf2ff"
        app.header_onpanel_soft = "#b9c7dd"

    if app.is_day_theme:
        clock_bg = app._blend_hex(panel_fill, "#ffffff", 0.08)
        clock_border = app._blend_hex(panel_fill, "#ffffff", 0.14)
        clock_shadow_stipple = "gray12"
    else:
        clock_bg = app._blend_hex("#0b223c", "#ffffff", 0.05)
        clock_border = app._blend_hex("#132744", "#ffffff", 0.08)
        clock_shadow_stipple = "gray12"

    app._clockcard_h = 110

    app.clockcard = RoundedFrame(
        app.clockbox,
        radius=RADIUS_MD,
        bg=clock_bg,
        border=clock_border,
        shadow=True,
        shadow_offset=SHADOW_SOFT,
        shadow_stipple=clock_shadow_stipple,
        gloss=True,
        gloss_inset=3,
        height=app._clockcard_h,
    )
    app.clockcard.pack(fill="x", pady=(0, 0))
    app.clockcard.pack_propagate(False)

    app.clock_inner = tk.Frame(app.clockcard, bg=clock_bg)
    app.clock_inner.place(relx=0.5, rely=0.5, anchor="center")

    app.clock_center = tk.Frame(app.clock_inner, bg=clock_bg)
    app.clock_center.pack(anchor="center")

    app.time_hhmm_lbl = tk.Label(
        app.clock_center,
        text="00:00",
        font=app.f_time_main,
        fg=app.header_onpanel_main,
        bg=clock_bg,
        anchor="center",
    )
    app.time_hhmm_lbl.pack(side="left")

    app.time_ss_lbl = tk.Label(
        app.clock_center,
        text=":00",
        font=app.f_time_sec,
        fg=app.header_onpanel_soft,
        bg=clock_bg,
        anchor="center",
    )
    app.time_ss_lbl.pack(side="left", padx=(4, 0))

    if app.DEBUG_LAYOUT:
        app.clockcard.configure(highlightthickness=2, highlightbackground="#ff66ff")

    # RIGHT (hours + spacer + weather)
    app.header_right = tk.Frame(app.header, bg=header_fill, width=right_w)
    app.header_right.grid(
        row=0,
        column=1,
        rowspan=2,
        sticky="nsew",
        padx=SP_12,
        pady=(SP_8, SP_12),
    )
    app.header_right.lift()
    app.header_right.grid_propagate(False)

    app.header_right.grid_columnconfigure(0, weight=1)
    app.header_right.grid_rowconfigure(0, weight=1)
    app.header_right.grid_rowconfigure(1, weight=0)
    app.header_right.grid_rowconfigure(2, weight=1)

    app._right_vspacer_top = tk.Frame(app.header_right, bg=header_fill)
    app._right_vspacer_top.grid(row=0, column=0, sticky="nsew")

    app.right_center = tk.Frame(app.header_right, bg=header_fill)
    app.right_center.grid(row=1, column=0, sticky="nsew", padx=(0, 12))

    app._right_vspacer_bottom = tk.Frame(app.header_right, bg=header_fill)
    app._right_vspacer_bottom.grid(row=2, column=0, sticky="nsew")

    app.right_center.grid_rowconfigure(0, weight=1)
    app.right_center.grid_columnconfigure(0, weight=0)
    app.right_center.grid_columnconfigure(1, weight=0)
    app.right_center.grid_columnconfigure(2, weight=0)

    app.hours_card = HoursCard(
        app.right_center,
        is_day_theme=app.is_day_theme,
        rounded_frame_cls=RoundedFrame,
    )
    app.weather_card = WeatherCard(
        app.right_center,
        is_day_theme=app.is_day_theme,
        ctx=app.ctx,
        logger=logger,
    )

    app.hours_card.grid(row=0, column=0, sticky="nsew")
    spacer = tk.Frame(app.right_center, bg=header_fill, width=40)
    spacer.grid(row=0, column=1, sticky="nsew")
    app.weather_card.grid(row=0, column=2, sticky="nsew", pady=6)

    app.hours_card.configure(width=hours_w, height=card_h)
    app.weather_card.configure(width=weather_w, height=card_h)

    app.hours_card.pack_propagate(False)
    app.weather_card.pack_propagate(False)

    if app.DEBUG_LAYOUT:
        app.header_right.configure(highlightthickness=2, highlightbackground="#ff00ff")

    # divider
    app.div = tk.Frame(app, bg=app.bg_root, height=3)
    app.div.pack(fill="x")

    app.div_hi_line = tk.Frame(app.div, bg=app.div_hi, height=1)
    app.div_hi_line.pack(fill="x", side="top")
    app.div_lo_line = tk.Frame(app.div, bg=app.div_lo, height=2)
    app.div_lo_line.pack(fill="x", side="top")

    # main
    app.main = tk.Frame(app, bg=app.bg_root)
    app.main.pack(fill="both", expand=True)

    app.main.grid_columnconfigure(0, weight=1, uniform="main")
    app.main.grid_columnconfigure(1, weight=0)
    app.main.grid_columnconfigure(2, weight=1, uniform="main")
    app.main.grid_rowconfigure(0, weight=1)

    app.vdiv = tk.Frame(app.main, bg="#1b3a5f", width=3)
    app.vdiv.grid(row=0, column=1, sticky="ns", padx=6, pady=14)

    app.agora = SectionFrame(
        app.main,
        "AGORA",
        is_day_theme=app.is_day_theme,
        rounded_frame_cls=RoundedFrame,
        card_cls=ClassCard,
    )
    app.prox = SectionFrame(
        app.main,
        "PRÓXIMAS",
        is_day_theme=app.is_day_theme,
        rounded_frame_cls=RoundedFrame,
        card_cls=ClassCard,
    )

    app.agora.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=(10, 14))
    app.prox.grid(row=0, column=2, sticky="nsew", padx=(8, 16), pady=(10, 14))

    app.after(0, app._layout_update)