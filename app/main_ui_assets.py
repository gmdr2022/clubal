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


def pil_contain_to_size(
    path: str,
    w: int,
    h: int,
    *,
    fill_ratio: float = 0.94,
    trim_transparent: bool = True,
):
    """
    Resize tipo 'CONTAIN' (encaixa sem cortar), centralizado, mantendo transparência.
    Melhorias:
    - recorta borda transparente externa quando existir
    - permite ocupar mais área útil do slot via fill_ratio
    Retorna PhotoImage (PIL).
    """
    im = _pil_open_rgba(path)

    if trim_transparent:
        try:
            alpha = im.getchannel("A")
            bbox = alpha.getbbox()
            if bbox:
                im = im.crop(bbox)
        except Exception:
            pass

    iw, ih = im.size
    if iw <= 0 or ih <= 0:
        return None

    try:
        fr = float(fill_ratio)
    except Exception:
        fr = 0.94

    if fr < 0.60:
        fr = 0.60
    if fr > 1.00:
        fr = 1.00

    fit_w = max(1, int(w * fr))
    fit_h = max(1, int(h * fr))

    scale = min(fit_w / iw, fit_h / ih)
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
                img = pil_contain_to_size(
                    p,
                    target_w,
                    target_h,
                    fill_ratio=0.96,
                    trim_transparent=True,
                )
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
    fallback_logo_path: str,
    first_image_in_dir: Callable[[str], Optional[str]],
) -> None:
    """
    Logo do CLIENTE (dinâmico):
    1) tenta a primeira imagem dentro de logo_cliente/
    2) se não houver, usa a logo completa interna do CLUBAL
    """
    try:
        p = first_image_in_dir(external_client_logo_dir)

        if not p and fallback_logo_path and os.path.exists(fallback_logo_path):
            p = fallback_logo_path

        if not p:
            if hasattr(app, "client_logo_lbl"):
                app.client_logo_lbl.configure(image="")
            return

        target_w = 360
        target_h = 160

        if hasattr(app, "client_slot") and app.client_slot.winfo_exists():
            app.client_slot.update_idletasks()
            sw = app.client_slot.winfo_width()
            sh = app.client_slot.winfo_height()
            if sw and sw > 10:
                target_w = max(220, sw - 4)
            if sh and sh > 10:
                target_h = max(110, sh - 4)

        img = None

        if PIL_OK:
            try:
                img = pil_contain_to_size(
                    p,
                    target_w,
                    target_h,
                    fill_ratio=0.985,
                    trim_transparent=True,
                )
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