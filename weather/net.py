from __future__ import annotations

import json
import ssl
import time
from typing import Any, Dict, Optional

import urllib.error
import urllib.request


__all__ = [
    "_ssl_context_best_effort",
    "_build_opener",
    "_http_get_bytes",
    "_http_get_json",
]


def _ssl_context_best_effort() -> ssl.SSLContext:
    try:
        import truststore  # type: ignore

        truststore.inject_into_ssl()
        return ssl.create_default_context()
    except Exception:
        pass

    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass

    return ssl.create_default_context()


def _build_opener(logger=None) -> urllib.request.OpenerDirector:
    proxies: Dict[str, str] = {}

    try:
        p_env = urllib.request.getproxies() or {}
        proxies.update({k.lower(): v for k, v in p_env.items() if v})
    except Exception:
        pass

    try:
        getproxies_registry = getattr(urllib.request, "getproxies_registry", None)
        if callable(getproxies_registry):
            p_reg_obj = getproxies_registry()
            if isinstance(p_reg_obj, dict):
                proxies.update({k.lower(): v for k, v in p_reg_obj.items() if v})
    except Exception:
        pass

    if logger:
        logger(f"[WEATHER] Proxies detectados: {proxies if proxies else 'nenhum'}")

    proxy_handler = urllib.request.ProxyHandler(proxies) if proxies else urllib.request.ProxyHandler({})
    https_handler = urllib.request.HTTPSHandler(context=_ssl_context_best_effort())
    return urllib.request.build_opener(proxy_handler, https_handler)


def _http_get_bytes(url: str, user_agent: str, timeout: int = 8, logger=None) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "*/*"},
        method="GET",
    )
    opener = _build_opener(logger=logger)

    last_exc: Optional[Exception] = None
    for attempt in (1, 2):
        try:
            if logger:
                logger(f"[WEATHER] GET bytes attempt {attempt} timeout={timeout}s url={url}")
            with opener.open(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            last_exc = e
            if logger:
                logger(f"[WEATHER] GET bytes error {type(e).__name__}: {e}")
            if attempt == 1:
                time.sleep(0.4)
                continue
            raise

    raise last_exc if last_exc else RuntimeError("HTTP bytes failed")


def _http_get_json(url: str, user_agent: str, timeout: int = 6, logger=None) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
        method="GET",
    )
    opener = _build_opener(logger=logger)

    last_exc: Optional[Exception] = None
    for attempt in (1, 2):
        try:
            if logger:
                logger(f"[WEATHER] HTTP attempt {attempt} timeout={timeout}s")

            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                if logger:
                    status = getattr(resp, "status", None) or getattr(resp, "code", "?")
                    logger(f"[WEATHER] HTTP {status} len={len(raw)}")
                return json.loads(raw)

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read(200).decode("utf-8", errors="replace")
            except Exception:
                pass
            if logger:
                logger(f"[WEATHER] HTTPError {e.code} {e.reason} body='{body}'")
            raise

        except urllib.error.URLError as e:
            last_exc = e
            if logger:
                logger(f"[WEATHER] URLError reason={repr(getattr(e, 'reason', e))}")
            if attempt == 1:
                time.sleep(0.4)
                continue
            raise

        except Exception as e:
            last_exc = e
            if logger:
                logger(f"[WEATHER] Exception {type(e).__name__}: {e}")
            if attempt == 1:
                time.sleep(0.4)
                continue
            raise

    raise last_exc if last_exc else RuntimeError("HTTP failed")