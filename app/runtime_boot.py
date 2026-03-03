from __future__ import annotations

import os
import sys
from typing import Callable

import tkinter as tk

from ui.header_layout import calc_header_geometry


def enable_windows_dpi_awareness() -> None:
    """
    Torna o processo DPI-aware para evitar variações de escala entre máquinas.
    Deve rodar ANTES de criar qualquer janela Tk (antes de ClubalApp()).
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes  # noqa

        try:
            # Windows 10 (1607+) — melhor opção: Per-Monitor V2
            DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
            ctypes.windll.user32.SetProcessDpiAwarenessContext(
                DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            )
            return
        except Exception:
            pass

        try:
            # Windows 8.1+ fallback
            PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(
                PROCESS_PER_MONITOR_DPI_AWARE
            )
            return
        except Exception:
            pass

        try:
            # Windows Vista+ fallback
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    except Exception:
        pass


def force_tk_scaling_96dpi(root: tk.Tk) -> float:
    """
    Força (ou não) a escala do Tk.

    Modo padrão (sem variável): FIXED_96DPI.
    Você pode mudar sem editar código usando variável de ambiente:

      CLUBAL_TK_SCALING=FIXED_96DPI   -> força 96dpi (96/72=1.3333)  [PADRÃO]
      CLUBAL_TK_SCALING=AUTO          -> não força nada
      CLUBAL_TK_SCALING=<float>       -> ex: 1.25 / 1.3333 / 1.5

    Retorna a escala aplicada (ou 0.0 se não aplicou).
    """
    try:
        mode = str(os.environ.get("CLUBAL_TK_SCALING", "FIXED_96DPI")).strip().upper()

        if mode in ("AUTO", "DEFAULT", "SYSTEM", "NONE"):
            return 0.0

        if mode in ("FIXED_96DPI", "96DPI", "FIXED"):
            fixed = 96.0 / 72.0
            root.tk.call("tk", "scaling", fixed)
            return float(fixed)

        try:
            val = float(mode.replace(",", "."))
            if 0.8 <= val <= 3.0:
                root.tk.call("tk", "scaling", val)
                return float(val)
        except Exception:
            pass

        return 0.0
    except Exception:
        return 0.0


def selftest_geometry(logger: Callable[[str], None]) -> None:
    """
    Teste rápido (sem UI) dos cálculos de geometria em resoluções comuns.
    Ative com: CLUBAL_SELFTEST=1
    """
    try:
        if str(os.environ.get("CLUBAL_SELFTEST", "0")).strip().upper() not in (
            "1",
            "TRUE",
            "YES",
            "ON",
        ):
            return

        tests = [
            (1360, 768),
            (1920, 1080),
            (2560, 1440),
            (3840, 2160),
        ]

        logger("[SELFTEST] Geometry test start")

        for sw, sh in tests:
            hours_w, weather_w, card_h, header_h, right_w = calc_header_geometry(sw, sh)

            ok1 = card_h <= (header_h - 16)
            ok2 = right_w <= sw

            logger(
                "[SELFTEST] "
                f"{sw}x{sh} -> hours_w={hours_w} weather_w={weather_w} "
                f"card_h={card_h} header_h={header_h} right_w={right_w} "
                f"ok_card_in_header={ok1} ok_right_fits_screen={ok2}"
            )

        logger("[SELFTEST] Geometry test end")

    except Exception as e:
        try:
            logger(f"[SELFTEST] Exception {type(e).__name__}: {e}")
        except Exception:
            pass