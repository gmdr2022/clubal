from __future__ import annotations

import os
import traceback

import tkinter as tk
import tkinter.font as tkfont

from ui.image_runtime import (
    PIL_OK,
    PIL_LANCZOS,
    PIL_NEAREST,
    img_path_try as _img_path_try,
    pil_new_rgba as _pil_new_rgba,
    pil_open_rgba as _pil_open_rgba,
    pil_photo_image as _pil_photo_image,
)


def pil_cover_to_size(card, p: str, w: int, h: int):
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


def draw_background(card, w: int, h: int) -> None:
    bg_name = "weather_day" if card.is_day_theme else "weather_night"
    p = _img_path_try(bg_name)

    try:
        card._log(f"[WEATHER][BG] PIL_OK={PIL_OK} bg_name={bg_name} path={p} exists={bool(p and os.path.exists(p))}")
    except Exception:
        pass

    key = (p, w, h, "PIL" if PIL_OK else "TK")
    if key != card._bg_key:
        card._bg_key = key
        card._bg_img = None

        if p and os.path.exists(p):
            if PIL_OK:
                try:
                    card._bg_img = pil_cover_to_size(card, p=p, w=w, h=h)
                    try:
                        card._log(f"[WEATHER][BG] loaded via PIL size={w}x{h}")
                    except Exception:
                        pass
                except Exception:
                    card._bg_img = None
                    try:
                        card._log("[WEATHER][BG] PIL load failed:\n" + traceback.format_exc())
                    except Exception:
                        pass

            if card._bg_img is None:
                try:
                    img = tk.PhotoImage(file=p)
                    if img.width() > w or img.height() > h:
                        fx = max(1, img.width() // max(1, w))
                        fy = max(1, img.height() // max(1, h))
                        f = max(fx, fy)
                        img = img.subsample(f)
                    card._bg_img = img
                    try:
                        card._log(f"[WEATHER][BG] loaded via TK orig={img.width()}x{img.height()} canvas={w}x{h}")
                    except Exception:
                        pass
                except Exception:
                    card._bg_img = None
                    try:
                        card._log("[WEATHER][BG] TK PhotoImage load failed:\n" + traceback.format_exc())
                    except Exception:
                        pass

    if card._bg_img:
        card.canvas.create_image(0, 0, anchor="nw", image=card._bg_img)
    else:
        card.canvas.create_rectangle(0, 0, w, h, fill=card.base_bg, outline="")

    if card._bg_img:
        card.canvas.create_image(0, 0, anchor="nw", image=card._bg_img)


def draw_frame(card, w: int, h: int) -> None:
    pad = 6
    card.canvas.create_rectangle(pad, pad, w - pad, h - pad, outline=card.border, width=2)
    card.canvas.create_line(pad + 2, pad + 2, w - pad - 2, pad + 2, fill=card.line_soft, width=2)


def glass_panel(card, x1, y1, x2, y2) -> None:
    w = int(max(1, x2 - x1))
    h = int(max(1, y2 - y1))

    if not PIL_OK:
        card.canvas.create_rectangle(x1, y1, x2, y2, fill=card.glass_fill, outline="")
        card.canvas.create_rectangle(x1, y1, x2, y2, outline=card.glass_edge, width=1)
        inset = 2
        card.canvas.create_rectangle(x1 + inset, y1 + inset, x2 - inset, y2 - inset, outline=card.glass_low, width=1)
        card.canvas.create_line(x1 + 3, y1 + 3, x2 - 3, y1 + 3, fill=card.glass_high, width=1)
        return

    alpha = int(max(35, min(180, getattr(card, "_glass_alpha", 105))))
    key = (w, h, alpha)

    img = card._glass_img_cache.get(key)

    if img is None:
        try:
            base_hex = (card.glass_fill or "#0a2a55").lstrip("#")
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
            card._glass_img_cache[key] = img
        except Exception:
            img = None
            card._glass_img_cache[key] = None

    if img is not None:
        card._glass_img_refs.append(img)
        if len(card._glass_img_refs) > 60:
            card._glass_img_refs = card._glass_img_refs[-30:]
        card.canvas.create_image(x1, y1, anchor="nw", image=img)
    else:
        card.canvas.create_rectangle(x1, y1, x2, y2, fill=card.glass_fill, outline="")

    card.canvas.create_rectangle(x1, y1, x2, y2, outline=card.glass_edge, width=1)
    inset = 2
    card.canvas.create_rectangle(x1 + inset, y1 + inset, x2 - inset, y2 - inset, outline=card.glass_low, width=1)
    card.canvas.create_line(x1 + 3, y1 + 3, x2 - 3, y1 + 3, fill=card.glass_high, width=1)


def tag_bar(card, x1: int, y1: int, x2: int, y2: int, text: str,
            fill: str, edge: str, txt: str, font_obj: tkfont.Font):
    w = int(x2 - x1)
    h = int(y2 - y1)

    if w < 40 or h < 16:
        pid = card.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=edge, width=1)
        tid = card.canvas.create_text(
            (x1 + x2) // 2, (y1 + y2) // 2,
            text=(text or "").strip(),
            fill=txt,
            font=font_obj
        )
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

    pid = card.canvas.create_polygon(pts, fill=fill, outline=edge, width=1, smooth=True)
    tid = card.canvas.create_text(
        (x1 + x2) // 2, (y1 + y2) // 2,
        anchor="center",
        text=(text or "").strip(),
        fill=txt,
        font=font_obj
    )
    return pid, tid


__all__ = [
    "pil_cover_to_size",
    "draw_background",
    "draw_frame",
    "glass_panel",
    "tag_bar",
]