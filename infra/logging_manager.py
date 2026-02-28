from __future__ import annotations

import os
import threading
import time
from typing import Optional


LOG_ROTATE_MAX_BYTES = 2 * 1024 * 1024
LOG_ARCHIVE_KEEP = 6
LOG_ARCHIVE_MAX_AGE_DAYS = 30

_log_lock = threading.Lock()


def _safe_unlink(path: Optional[str]) -> None:
    if not path:
        return
    try:
        os.remove(path)
    except Exception:
        pass


def _ensure_dir(path: Optional[str]) -> bool:
    if not path:
        return False
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False


def _cleanup_log_archive(log_archive_dir: Optional[str]) -> None:
    try:
        if not log_archive_dir or not os.path.isdir(log_archive_dir):
            return

        files = []
        now = time.time()
        max_age = LOG_ARCHIVE_MAX_AGE_DAYS * 86400

        for name in os.listdir(log_archive_dir):
            p = os.path.join(log_archive_dir, name)
            if not os.path.isfile(p):
                continue
            try:
                st = os.stat(p)
            except Exception:
                continue

            if max_age > 0 and (now - st.st_mtime) > max_age:
                _safe_unlink(p)
                continue

            files.append((st.st_mtime, p))

        files.sort(reverse=True)
        for _mtime, p in files[LOG_ARCHIVE_KEEP:]:
            _safe_unlink(p)

    except Exception:
        pass


def rotate_logs_if_needed(log_path: Optional[str], log_archive_dir: Optional[str], logger=None) -> None:
    try:
        if not log_path or not log_archive_dir:
            return

        if not os.path.exists(log_path):
            _cleanup_log_archive(log_archive_dir)
            return

        size = os.path.getsize(log_path)
        if size < LOG_ROTATE_MAX_BYTES:
            _cleanup_log_archive(log_archive_dir)
            return

        if not _ensure_dir(log_archive_dir):
            return

        ts = time.strftime("%Y%m%d_%H%M%S")
        archived = os.path.join(log_archive_dir, f"clubal_{ts}.log")
        try:
            os.replace(log_path, archived)
        except Exception:
            with open(log_path, "rb") as src, open(archived, "wb") as dst:
                dst.write(src.read())
            with open(log_path, "w", encoding="utf-8"):
                pass

        if logger:
            logger(f"[LOG] Rotated clubal.log -> {archived}")

        _cleanup_log_archive(log_archive_dir)

    except Exception as e:
        if logger:
            logger(f"[LOG] Rotate error {type(e).__name__}: {e}")


def write_log(log_path: Optional[str], logs_dir: Optional[str], msg: str) -> None:
    try:
        if not log_path:
            return

        with _log_lock:
            if logs_dir:
                os.makedirs(logs_dir, exist_ok=True)
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass