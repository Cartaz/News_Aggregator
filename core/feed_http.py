"""Strategia HTTP per download feed, WAF fallback e cache validation."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Mapping

import requests
from requests.exceptions import RequestException, Timeout

from config.constants import FeedDefaults
from core.exceptions import FeedFetchError, RefreshCancelledError

logger = logging.getLogger(__name__)

try:
    from curl_cffi import requests as cf_requests  # type: ignore[import-untyped]
    _HAS_CURL_CFFI: bool = True
except ImportError:
    cf_requests = None  # type: ignore[assignment]
    _HAS_CURL_CFFI = False

try:
    import brotli  # noqa: F401
    _HAS_BROTLI: bool = True
except ImportError:
    _HAS_BROTLI = False


@dataclass(frozen=True)
class HttpFetchResult:
    """Risultato HTTP con validator utili ai refresh condizionali."""

    content: bytes
    etag: str = ""
    last_modified: str = ""
    not_modified: bool = False


def _raise_if_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise RefreshCancelledError()


def _accept_encoding_value() -> str:
    if _HAS_BROTLI:
        return "gzip, deflate, br"
    logger.debug(
        "brotli non installato: Accept-Encoding senza 'br'. "
        "Installa il pacchetto 'Brotli' per supporto completo."
    )
    return "gzip, deflate"


def _browser_headers() -> dict[str, str]:
    return {
        "User-Agent": FeedDefaults.USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
        "Accept-Encoding": _accept_encoding_value(),
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def _conditional_headers(etag: str, last_modified: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return headers


def _metadata_result(
    content: bytes,
    headers: Mapping[str, Any],
    *,
    not_modified: bool = False,
    fallback_etag: str = "",
    fallback_last_modified: str = "",
) -> HttpFetchResult:
    return HttpFetchResult(
        content=content,
        etag=str(headers.get("ETag", "") or fallback_etag),
        last_modified=str(
            headers.get("Last-Modified", "") or fallback_last_modified
        ),
        not_modified=not_modified,
    )


def _looks_like_cloudflare_challenge(content: bytes) -> bool:
    if not content:
        return False
    head: bytes = content[:2048].lower()
    return b"just a moment" in head or b"cf-browser-verification" in head


def fetch_url_response(
    url: str,
    timeout: int | None = None,
    *,
    etag: str = "",
    last_modified: str = "",
    cancel_event: threading.Event | None = None,
) -> HttpFetchResult:
    """Scarica un URL restituendo contenuto e validator HTTP.

    Quando sono presenti validator, invia ``If-None-Match`` e/o
    ``If-Modified-Since``. Una risposta ``304 Not Modified`` è un risultato
    valido: ``not_modified`` sarà True e ``content`` resterà vuoto.

    ``cancel_event`` non interrompe una richiesta già dentro la libreria HTTP,
    ma impedisce fallback o richieste successive dopo una cancellazione.
    """
    actual_timeout: int = timeout or FeedDefaults.REQUEST_TIMEOUT_SECONDS
    conditional = _conditional_headers(etag, last_modified)
    request_headers = _browser_headers()
    request_headers.update(conditional)
    last_error: FeedFetchError | None = None

    _raise_if_cancelled(cancel_event)
    try:
        logger.debug("GET %s (requests, timeout=%ds)", url, actual_timeout)
        response: requests.Response = requests.get(
            url,
            timeout=actual_timeout,
            headers=request_headers,
            allow_redirects=True,
        )
        if response.status_code == 304:
            logger.debug("HTTP 304 Not Modified: %s", url)
            return _metadata_result(
                b"",
                response.headers,
                not_modified=True,
                fallback_etag=etag,
                fallback_last_modified=last_modified,
            )
        response.raise_for_status()
        if response.content:
            ce = response.headers.get("Content-Encoding", "").lower()
            if "br" in ce and not _HAS_BROTLI:
                logger.warning(
                    "Risposta brotli da %s ma brotli non installato; "
                    "installa 'Brotli' per decomprimerla correttamente.",
                    url,
                )
            return _metadata_result(response.content, response.headers)
        last_error = FeedFetchError(url, "risposta vuota")
    except requests.HTTPError as exc:
        if response.status_code == 403:
            last_error = FeedFetchError(
                url,
                "403 Forbidden — WAF blocca requests, provo curl_cffi",
            )
        else:
            last_error = FeedFetchError(url, str(exc))
    except Timeout:
        last_error = FeedFetchError(url, f"timeout ({actual_timeout}s)")
    except RequestException as exc:
        last_error = FeedFetchError(url, str(exc))

    _raise_if_cancelled(cancel_event)
    if _HAS_CURL_CFFI:
        try:
            logger.debug("GET %s (curl_cffi, chrome120)", url)
            cf_response: Any = cf_requests.get(
                url,
                impersonate="chrome120",
                timeout=actual_timeout,
                allow_redirects=True,
                headers=conditional or None,
            )
            if cf_response.status_code == 304:
                logger.debug("HTTP 304 Not Modified via curl_cffi: %s", url)
                return _metadata_result(
                    b"",
                    cf_response.headers,
                    not_modified=True,
                    fallback_etag=etag,
                    fallback_last_modified=last_modified,
                )
            if cf_response.status_code == 200 and cf_response.content:
                content_bytes: bytes = bytes(cf_response.content)
                if _looks_like_cloudflare_challenge(content_bytes):
                    raise FeedFetchError(
                        url,
                        "Cloudflare JS challenge non superabile senza "
                        "browser reale. Prova con un URL diretto del feed RSS.",
                    )
                return _metadata_result(content_bytes, cf_response.headers)
            if cf_response.status_code == 403:
                last_error = FeedFetchError(
                    url,
                    "403 Forbidden — WAF Cloudflare blocca anche curl_cffi. "
                    "Prova con URL diretto del feed o un proxy RSS esterno.",
                )
            else:
                last_error = FeedFetchError(
                    url, f"curl_cffi: HTTP {cf_response.status_code}"
                )
        except RefreshCancelledError:
            raise
        except FeedFetchError:
            raise
        except Exception as exc:
            logger.debug("curl_cffi fallito: %s", exc)

    _raise_if_cancelled(cancel_event)
    raise last_error or FeedFetchError(url, "errore sconosciuto")


def fetch_url(url: str, timeout: int | None = None) -> bytes:
    """API compatibile: scarica e restituisce solo i bytes."""
    return fetch_url_response(url, timeout).content


def fetch_url_simple(url: str, timeout: int) -> bytes:
    """Scarica un URL con solo ``requests`` (senza fallback WAF)."""
    try:
        logger.debug("GET %s (requests, timeout=%ds)", url, timeout)
        response: requests.Response = requests.get(
            url,
            timeout=timeout,
            headers=_browser_headers(),
            allow_redirects=True,
        )
        response.raise_for_status()
        return response.content
    except Timeout as exc:
        raise FeedFetchError(url, f"timeout ({timeout}s)") from exc
    except requests.HTTPError as exc:
        if response.status_code == 403:
            raise FeedFetchError(
                url,
                "403 Forbidden — WAF blocca il download. Prova un URL "
                "diretto del feed o un proxy RSS esterno.",
            ) from exc
        raise FeedFetchError(url, str(exc)) from exc
    except RequestException as exc:
        raise FeedFetchError(url, str(exc)) from exc


__all__ = [
    "HttpFetchResult",
    "fetch_url",
    "fetch_url_response",
    "fetch_url_simple",
]
