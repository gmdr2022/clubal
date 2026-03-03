from __future__ import annotations

import os
from typing import Any, Iterable, Optional, Tuple, cast

# ---------------------------------
# Pillow opcional
# ---------------------------------
try:
    from PIL import Image, ImageTk  # type: ignore
    PIL_OK = True
except Exception:
    Image = None
    ImageTk = None
    PIL_OK = False


def _pil_image_module() -> Any:
    if not PIL_OK or Image is None:
        raise RuntimeError("Pillow unavailable")
    return cast(Any, Image)


def _pil_imagetk_module() -> Any:
    if not PIL_OK or ImageTk is None:
        raise RuntimeError("Pillow unavailable")
    return cast(Any, ImageTk)


if PIL_OK:
    _pil_img_mod = _pil_image_module()
    try:
        PIL_LANCZOS = _pil_img_mod.Resampling.LANCZOS
        PIL_NEAREST = _pil_img_mod.Resampling.NEAREST
    except Exception:
        PIL_LANCZOS = getattr(_pil_img_mod, "LANCZOS", 1)
        PIL_NEAREST = getattr(_pil_img_mod, "NEAREST", 0)
else:
    PIL_LANCZOS = 1
    PIL_NEAREST = 0


def pil_open_rgba(path: str):
    return _pil_image_module().open(path).convert("RGBA")


def pil_new_rgba(size: Tuple[int, int], color: Tuple[int, int, int, int]):
    return _pil_image_module().new("RGBA", size, color)


def pil_photo_image(image_obj: Any):
    return _pil_imagetk_module().PhotoImage(image_obj)


# ---------------------------------
# Busca compartilhada de assets
# ---------------------------------
_SEARCH_DIRS: list[str] = []


def configure_image_search_dirs(search_dirs: Iterable[str]) -> None:
    global _SEARCH_DIRS

    out: list[str] = []

    try:
        for d in search_dirs or []:
            try:
                s = str(d or "").strip()
            except Exception:
                s = ""

            if s and s not in out:
                out.append(s)
    except Exception:
        out = []

    _SEARCH_DIRS = out


def first_image_in_dir(dir_path: str) -> Optional[str]:
    """
    Retorna o caminho da primeira imagem encontrada em dir_path.
    Preferência: PNG/JPG/JPEG/GIF. Ordena por nome para previsibilidade.
    """
    try:
        if not dir_path or not os.path.isdir(dir_path):
            return None

        files = []
        for name in os.listdir(dir_path):
            p = os.path.join(dir_path, name)
            if not os.path.isfile(p):
                continue

            low = name.lower()
            if low.endswith((".png", ".jpg", ".jpeg", ".gif")):
                files.append(p)

        if not files:
            return None

        files.sort(key=lambda x: os.path.basename(x).lower())
        return files[0]

    except Exception:
        return None


def img_path_try(base: str) -> Optional[str]:
    """
    Procura assets em múltiplas pastas configuradas.
    Aceita 'base' com ou sem extensão.
    """
    try:
        b = str(base or "").strip()
        if not b:
            return None

        has_ext = b.lower().endswith((".png", ".gif", ".jpg", ".jpeg"))

        candidates = []
        if has_ext:
            candidates.append(b)
        else:
            candidates.extend([
                b + ".png",
                b + ".PNG",
                b + ".jpg",
                b + ".JPG",
                b + ".jpeg",
                b + ".JPEG",
                b + ".gif",
                b + ".GIF",
            ])

        for d in _SEARCH_DIRS:
            for name in candidates:
                p = os.path.join(d, name)
                if os.path.exists(p):
                    return p

        return None

    except Exception:
        return None