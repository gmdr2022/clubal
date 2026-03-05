from __future__ import annotations

import os
from typing import Optional

import tkinter as tk

from ui.image_runtime import (
    PIL_OK,
    PIL_LANCZOS,
    pil_new_rgba as _pil_new_rgba,
    pil_open_rgba as _pil_open_rgba,
    pil_photo_image as _pil_photo_image,
)


def pil_icon_to_size(p: str, target: int):
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


def update_icon(card, icon_path: Optional[str]) -> None:
    if not icon_path or not os.path.exists(icon_path):
        card._icon_img = None
        card._icon_key = None
        return

    target = 112
    if getattr(card, "_layout_geom", None):
        try:
            target = int(card._layout_geom.get("icon_target", target))
        except Exception:
            target = target

    target = max(64, int(target))

    key = (icon_path, target, "PIL" if PIL_OK else "TK")
    if key == getattr(card, "_icon_key", None):
        return
    card._icon_key = key

    card._icon_img = None
    try:
        if PIL_OK:
            try:
                card._icon_img = pil_icon_to_size(p=icon_path, target=target)
            except Exception:
                card._icon_img = None

        if card._icon_img is None:
            img = tk.PhotoImage(file=icon_path)
            if img.width() > target or img.height() > target:
                fx = max(1, img.width() // max(1, target))
                fy = max(1, img.height() // max(1, target))
                f = max(fx, fy)
                img = img.subsample(f)
            card._icon_img = img
    except Exception:
        card._icon_img = None


def place_icon(card) -> None:
    if not getattr(card, "_layout_geom", None) or "icon_box" not in card._layout_geom:
        return

    if "icon_img" in getattr(card, "_ids", {}):
        try:
            card.canvas.delete(card._ids["icon_img"])
        except Exception:
            pass
        card._ids.pop("icon_img", None)

    if not getattr(card, "_icon_img", None):
        return

    try:
        cx, cy = card._layout_geom.get("icon_center", (None, None))
    except Exception:
        cx, cy = (None, None)

    if cx is None or cy is None:
        x1, y1, x2, y2 = card._layout_geom["icon_box"]
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

    card._ids["icon_img"] = card.canvas.create_image(int(cx), int(cy), anchor="center", image=card._icon_img)


__all__ = [
    "pil_icon_to_size",
    "place_icon",
    "update_icon",
]