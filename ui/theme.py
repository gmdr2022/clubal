from __future__ import annotations

import time


SP_4 = 4
SP_8 = 8
SP_12 = 12
SP_16 = 16
SP_20 = 20
SP_24 = 24
SP_32 = 32

RADIUS_SM = 14
RADIUS_MD = 18
RADIUS_LG = 22

SHADOW_SOFT = (2, 3)
SHADOW_MD = (3, 4)

MS_CARD_ROTATE = 4500
MS_SCROLL_TICK = 25
MS_MARQUEE_TICK = 25
MS_MARQUEE_SPEED_PX = 1
MS_SECTION_SCROLL_SPEED_PX = 1
MS_HOURS_ROTATE = 16000


def theme_is_day() -> bool:
    h = time.localtime().tm_hour
    return 6 <= h <= 17


def build_app_palette(is_day_theme: bool) -> dict:
    return {
        "bg_root": "#f5f7fb" if is_day_theme else "#06101f",
        "bg_header": "#f5f7fb" if is_day_theme else "#071a33",
        "fg_primary": "#0b2d4d" if is_day_theme else "#eaf2ff",
        "fg_soft": "#5c6f86" if is_day_theme else "#b9c7dd",
        "div_main": "#cfd8e5" if is_day_theme else "#0f2543",
        "div_hi": "#e9eef5" if is_day_theme else "#16365f",
        "div_lo": "#b7c3d4" if is_day_theme else "#08172c",
    }