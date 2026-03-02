from __future__ import annotations

from typing import Tuple


def calc_header_geometry(sw: int, sh: int) -> Tuple[int, int, int, int, int]:
    """
    Retorna:
    (hours_w, weather_w, card_h, header_h, right_w)
    """

    is_big_screen = (sh >= 1200) or (sw >= 2560)

    max_card_h = 520 if is_big_screen else 420
    max_header_h = 680 if is_big_screen else 520

    card_h = int(sh * 0.28)
    card_h = max(220, min(max_card_h, card_h))

    header_h = int(sh * 0.42)
    header_h = max(header_h, card_h + 96)
    header_h = max(320, min(max_header_h, header_h))

    card_h = min(card_h, header_h - 24)
    card_h = max(170, card_h)

    unit_w = int(sw * 0.205)
    unit_w = max(340, min(520 if is_big_screen else 480, unit_w))

    hours_w = unit_w * 2 + 8
    hours_w = max(620, hours_w - 120)

    weather_w = unit_w

    right_w = int(hours_w + 40 + weather_w) + 24

    return hours_w, weather_w, card_h, header_h, right_w