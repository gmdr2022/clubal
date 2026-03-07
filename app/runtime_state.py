from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from infra.logging_manager import rotate_logs_if_needed, write_log
from ui.image_runtime import configure_image_search_dirs


@dataclass(frozen=True)
class RuntimeState:
    graphics_dir: str
    graphics_logos_dir: str
    graphics_brand_dir: str
    graphics_client_dir: str
    external_client_logo_dir: str

    clubal_icon_file: str
    client_logo_dirname: str
    client_logo_fallback: str

    logs_dir: Optional[str]
    log_path: Optional[str]
    log_archive_dir: Optional[str]

    excel_path: str

    log: Callable[[str], None] = field(repr=False)


def build_runtime_state(ctx: Any) -> RuntimeState:
    graphics_dir = str(ctx.paths.assets_dir)

    graphics_logos_dir = os.path.join(graphics_dir, "logos")
    graphics_brand_dir = os.path.join(graphics_logos_dir, "brand")
    graphics_client_dir = os.path.join(graphics_logos_dir, "client")

    clubal_icon_file = "CLUBAL_ICO.png"
    client_logo_dirname = "logo_cliente"
    client_logo_fallback = "CLUBAL_LOGO.png"

    external_client_logo_dir = os.path.join(str(ctx.paths.data_dir), client_logo_dirname)

    configure_image_search_dirs([
        graphics_dir,
        graphics_logos_dir,
        graphics_brand_dir,
        graphics_client_dir,
        external_client_logo_dir,
        os.path.join(graphics_dir, "weather", "icons"),
        os.path.join(graphics_dir, "weather", "bg"),
    ])

    logs_dir = str(ctx.paths.logs_dir) if ctx.paths.logs_dir is not None else None
    log_path = os.path.join(logs_dir, "clubal.log") if logs_dir else None
    log_archive_dir = os.path.join(logs_dir, "archive") if logs_dir else None

    excel_path = os.path.join(str(ctx.paths.data_dir), "grade.xlsx")

    def _log(msg: str) -> None:
        try:
            rotate_logs_if_needed(log_path, log_archive_dir)
            write_log(log_path, logs_dir, msg)
        except Exception:
            pass

    return RuntimeState(
        graphics_dir=graphics_dir,
        graphics_logos_dir=graphics_logos_dir,
        graphics_brand_dir=graphics_brand_dir,
        graphics_client_dir=graphics_client_dir,
        external_client_logo_dir=external_client_logo_dir,
        clubal_icon_file=clubal_icon_file,
        client_logo_dirname=client_logo_dirname,
        client_logo_fallback=client_logo_fallback,
        logs_dir=logs_dir,
        log_path=log_path,
        log_archive_dir=log_archive_dir,
        excel_path=excel_path,
        log=_log,
    )