from __future__ import annotations

import os
from typing import Any, Callable, Optional

import tkinter as tk

from ui.image_runtime import (
    PIL_LANCZOS,
    PIL_OK,
    pil_new_rgba as _pil_new_rgba,
    pil_open_rgba as _pil_open_rgba,
    pil_photo_image as _pil_photo_image,
)


def pil_contain_to_size(path: str, w: int, h: int):
    """
    Resize tipo 'CONTAIN' (encaixa sem cortar), centralizado, mantendo transparência.
    Retorna PhotoImage (PIL).
    """
    im = _pil_open_rgba(path)
    iw, ih = im.size
    if iw <= 0 or ih <= 0:
        return None

    scale = min(w / iw, h / ih)
    nw = max(1, int(iw * scale))
    nh = max(1, int(ih * scale))
    im = im.resize((nw, nh), PIL_LANCZOS)

    canvas = _pil_new_rgba((w, h), (0, 0, 0, 0))
    x = (w - nw) // 2
    y = (h - nh) // 2
    canvas.paste(im, (x, y), im)

    return _pil_photo_image(canvas)


def refresh_logo(
    app: Any,
    *,
    graphics_brand_dir: str,
    clubal_icon_file: str,
    img_path_try: Callable[[str], Optional[str]],
) -> None:
    """
    Logo do CLUBAL (fixo):
    Sempre usa graphics/logos/brand/CLUBAL_ICO.png
    """
    p = os.path.join(graphics_brand_dir, clubal_icon_file)
    if not os.path.exists(p):
        p = img_path_try("CLUBAL_ICO") or img_path_try(clubal_icon_file)

    if not p or not os.path.exists(p):
        if hasattr(app, "logo_lbl"):
            app.logo_lbl.configure(image="")
        return

    try:
        target_w = 150
        target_h = 150

        if hasattr(app, "clubal_slot") and app.clubal_slot.winfo_exists():
            app.clubal_slot.update_idletasks()
            sw = app.clubal_slot.winfo_width()
            sh = app.clubal_slot.winfo_height()
            if sw and sw > 10:
                target_w = max(90, sw - 10)
            if sh and sh > 10:
                target_h = max(90, sh - 10)

        img = None

        if PIL_OK:
            try:
                img = pil_contain_to_size(p, target_w, target_h)
            except Exception:
                img = None

        if img is None:
            tkimg = tk.PhotoImage(file=p)
            fx = max(1, (tkimg.width() + target_w - 1) // target_w) if tkimg.width() > target_w else 1
            fy = max(1, (tkimg.height() + target_h - 1) // target_h) if tkimg.height() > target_h else 1
            f = max(fx, fy)
            if f > 1:
                tkimg = tkimg.subsample(f)
            img = tkimg

        app.logo_img = img
        app.logo_lbl.configure(image=app.logo_img)

    except Exception:
        if hasattr(app, "logo_lbl"):
            app.logo_lbl.configure(image="")


def refresh_client_logo(
    app: Any,
    *,
    external_client_logo_dir: str,
    fallback_client_dir: str,
    first_image_in_dir: Callable[[str], Optional[str]],
) -> None:
    """
    Logo do CLIENTE (dinâmico):
    1) tenta a primeira imagem dentro de logo_cliente/
    2) se não houver, usa fallback interno em graphics/logos/client/
    """
    try:
        p = first_image_in_dir(external_client_logo_dir)

        if not p:
            p = first_image_in_dir(fallback_client_dir)

        if not p:
            if hasattr(app, "client_logo_lbl"):
                app.client_logo_lbl.configure(image="")
            return

        target_w = 320
        target_h = 150

        if hasattr(app, "client_slot") and app.client_slot.winfo_exists():
            app.client_slot.update_idletasks()
            sw = app.client_slot.winfo_width()
            sh = app.client_slot.winfo_height()
            if sw and sw > 10:
                target_w = max(160, sw - 10)
            if sh and sh > 10:
                target_h = max(90, sh - 10)

        img = None

        if PIL_OK:
            try:
                img = pil_contain_to_size(p, target_w, target_h)
            except Exception:
                img = None

        if img is None:
            tkimg = tk.PhotoImage(file=p)
            fx = max(1, (tkimg.width() + target_w - 1) // target_w) if tkimg.width() > target_w else 1
            fy = max(1, (tkimg.height() + target_h - 1) // target_h) if tkimg.height() > target_h else 1
            f = max(fx, fy)
            if f > 1:
                tkimg = tkimg.subsample(f)
            img = tkimg

        app.client_logo_img = img
        app.client_logo_lbl.configure(image=app.client_logo_img)
        app.client_logo_lbl.place(relx=0.5, rely=0.5, anchor="center")

    except Exception:
        if hasattr(app, "client_logo_lbl"):
            app.client_logo_lbl.configure(image="")