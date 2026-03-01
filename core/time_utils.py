from __future__ import annotations

from typing import Optional, Tuple


def parse_hhmm(v: object) -> Optional[int]:
    """
    Aceita:
    - "HH:MM"
    - "HH:MM:SS"
    - datetime.time / datetime.datetime
    - float/int do Excel (fração do dia), ex: 0.5 = 12:00, 0.958333 = 23:00
      (se vier número grande, usa apenas a parte fracionária)

    Retorna minutos desde 00:00 (0..1439)
    """
    try:
        if v is None:
            return None

        if hasattr(v, "hour") and hasattr(v, "minute"):
            try:
                hh = int(getattr(v, "hour"))
                mm = int(getattr(v, "minute"))
                if 0 <= hh <= 23 and 0 <= mm <= 59:
                    return hh * 60 + mm
            except Exception:
                pass

        if isinstance(v, (int, float)):
            f = float(v)
            frac = f % 1.0
            if frac < 0:
                frac = -frac
            mins = int(round(frac * 24.0 * 60.0))
            mins = mins % (24 * 60)
            return mins

        s = str(v).strip()
        if not s:
            return None

        if ":" not in s:
            try:
                f = float(s.replace(",", "."))
                frac = f % 1.0
                if frac < 0:
                    frac = -frac
                mins = int(round(frac * 24.0 * 60.0))
                mins = mins % (24 * 60)
                return mins
            except Exception:
                return None

        parts = s.split(":")
        if len(parts) < 2:
            return None

        hh = int(parts[0])
        mm = int(parts[1])

        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return hh * 60 + mm

        return None
    except Exception:
        return None


def split_clock_hhmm_ss(t: str) -> Tuple[str, str]:
    """
    Recebe "HH:MM:SS" e devolve ("HH:MM", "SS").
    Fallback seguro se vier algo diferente.
    """
    try:
        s = str(t).strip()

        if len(s) >= 8 and s[2] == ":" and s[5] == ":":
            return s[:5], s[6:8]

        parts = s.split(":")
        if len(parts) >= 3:
            return f"{parts[0]:0>2}:{parts[1]:0>2}", f"{parts[2]:0>2}"[:2]
        if len(parts) == 2:
            return f"{parts[0]:0>2}:{parts[1]:0>2}", "00"

        return s[:5], "00"
    except Exception:
        return "00:00", "00"


def fmt_hhmm(mins: Optional[int]) -> str:
    if mins is None:
        return "—"

    hh = mins // 60
    mm = mins % 60

    if mm == 0:
        return f"{hh:02d}H"

    return f"{hh:02d}:{mm:02d}"