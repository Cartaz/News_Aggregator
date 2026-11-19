"""Strategia HTTP per download feed, WAF fallback e cache validation."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import threading
from dataclasses import dataclass
from collections.abc import Iterable, Mapping
from typing import Any

import requests
from requests.exceptions import RequestException, Timeout

from config.constants import FeedDefaults
from core.exceptions import FeedFetchError, RefreshCancelledError

logger = logging.getLogger(__name__)

# curl_cffi is a relatively heavy optional native dependency. Keep it out of
# the process until the normal requests transport actually needs the WAF
# fallback. These names remain module-level for compatibility with focused
# tests and diagnostics.
cf_requests: Any | None = None
_HAS_CURL_CFFI: bool | None = None
_HAS_BROTLI = importlib.util.find_spec("brotli") is not None

# A feed is text: anything beyond this is broken or hostile, not news.
MAX_FEED_BYTES = 10 * 1024 * 1024
_CHUNK_SIZE = 64 * 1024
# Responses that typically mean "your client fingerprint was blocked".
_WAF_STATUSES = frozenset({403, 503})
_IMPERSONATE = "chrome120"


class ResponseTooLargeError(ValueError):
    """The response body exceeded the configured download limit."""

    def __init__(self, limit: int) -> None:
        super().__init__(f"risposta oltre il limite di {limit} byte")


@dataclass(frozen=True, slots=True)
class HttpFetchResult:
    """Risultato HTTP con validator utili ai refresh condizionali."""

    content: bytes
    etag: str = ""
    last_modified: str = ""
    not_modified: bool = False


def _get_curl_requests() -> Any | None:
    """Load curl_cffi only when the primary requests transport has failed."""
    global _HAS_CURL_CFFI, cf_requests

    if cf_requests is not None:
        _HAS_CURL_CFFI = True
        return cf_requests
    if _HAS_CURL_CFFI is False:
        return None
    try:
        cf_requests = importlib.import_module("curl_cffi.requests")
    except ImportError:
        _HAS_CURL_CFFI = False
        return None
    _HAS_CURL_CFFI = True
    return cf_requests


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


def read_limited(chunks: Iterable[bytes], limit: int) -> bytes:
    """Join streamed chunks, refusing bodies larger than ``limit`` bytes."""
    collected: list[bytes] = []
    total = 0
    for chunk in chunks:
        if not chunk:
            continue
        total += len(chunk)
        if total > limit:
            raise ResponseTooLargeError(limit)
        collected.append(chunk)
    return b"".join(collected)


def fetch_url_response(
    url: str,
    timeout: int | None = None,
    *,
    etag: str = "",
    last_modified: str = "",
    cancel_event: threading.Event | None = None,
    max_bytes: int = MAX_FEED_BYTES,
) -> HttpFetchResult:
    """Scarica un URL restituendo contenuto e validator HTTP.

    Quando sono presenti validator, invia ``If-None-Match`` e/o
    ``If-Modified-Since``. Una risposta ``304 Not Modified`` è un risultato
    valido: ``not_modified`` sarà True e ``content`` resterà vuoto.

    Il fallback ``curl_cffi`` (impronta TLS di un browser) viene usato solo
    quando la risposta indica un blocco anti-bot: 403/503, challenge
    Cloudflare o errore TLS. Timeout, DNS, 404 e 5xx generici falliscono
    subito, senza raddoppiare attese e richieste.

    ``cancel_event`` non interrompe una richiesta già dentro la libreria HTTP,
    ma impedisce fallback o richieste successive dopo una cancellazione.
    """
    actual_timeout: int = timeout or FeedDefaults.REQUEST_TIMEOUT_SECONDS
    conditional = _conditional_headers(etag, last_modified)
    request_headers = _browser_headers()
    request_headers.update(conditional)

    _raise_if_cancelled(cancel_event)
    try:
        logger.debug("GET %s (requests, timeout=%ds)", url, actual_timeout)
        with requests.get(
            url,
            timeout=actual_timeout,
            headers=request_headers,
            allow_redirects=True,
            stream=True,
        ) as response:
            status = response.status_code
            if status == 304:
                return _metadata_result(
                    b"",
                    response.headers,
                    not_modified=True,
                    fallback_etag=etag,
                    fallback_last_modified=last_modified,
                )
            if status in _WAF_STATUSES:
                blocked = FeedFetchError(
                    url, f"HTTP {status} (possibile blocco anti-bot)", status_code=status
                )
            else:
                response.raise_for_status()
                content = read_limited(response.iter_content(_CHUNK_SIZE), max_bytes)
                if not content:
                    raise FeedFetchError(url, "risposta vuota", status_code=status)
                if not _looks_like_cloudflare_challenge(content):
                    return _metadata_result(content, response.headers)
                blocked = FeedFetchError(
                    url, "challenge anti-bot Cloudflare", status_code=status
                )
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        raise FeedFetchError(url, str(exc), status_code=status) from exc
    except requests.exceptions.SSLError as exc:
        # Some WAFs reject the Python TLS fingerprint during the handshake.
        blocked = FeedFetchError(url, f"errore TLS: {exc}")
    except Timeout as exc:
        raise FeedFetchError(url, f"timeout ({actual_timeout}s)") from exc
    except RequestException as exc:
        raise FeedFetchError(url, str(exc)) from exc
    except ResponseTooLargeError as exc:
        raise FeedFetchError(url, str(exc)) from exc

    _raise_if_cancelled(cancel_event)
    return _fetch_with_browser_fingerprint(
        url, actual_timeout, conditional, etag, last_modified, max_bytes, blocked
    )


def _fetch_with_browser_fingerprint(
    url: str,
    timeout: int,
    conditional: dict[str, str],
    etag: str,
    last_modified: str,
    max_bytes: int,
    blocked: FeedFetchError,
) -> HttpFetchResult:
    """Retry a blocked request through curl_cffi, or report the original block."""
    curl_requests = _get_curl_requests()
    if curl_requests is None:
        raise blocked
    try:
        logger.debug("GET %s (curl_cffi, %s)", url, _IMPERSONATE)
        with curl_requests.Session() as session:
            response = session.get(
                url,
                impersonate=_IMPERSONATE,
                timeout=timeout,
                allow_redirects=True,
                headers=conditional or None,
                stream=True,
            )
            try:
                status = response.status_code
                if status == 304:
                    return _metadata_result(
                        b"",
                        response.headers,
                        not_modified=True,
                        fallback_etag=etag,
                        fallback_last_modified=last_modified,
                    )
                if status != 200:
                    raise FeedFetchError(
                        url,
                        f"bloccato anche dal fallback browser (HTTP {status}). "
                        "Prova con l'URL diretto del feed.",
                        status_code=status,
                    )
                content = read_limited(response.iter_content(_CHUNK_SIZE), max_bytes)
            finally:
                response.close()
    except FeedFetchError:
        raise
    except ResponseTooLargeError as exc:
        raise FeedFetchError(url, str(exc)) from exc
    except Exception as exc:
        # Network failures are routine for a feed reader; the feed manager
        # already logs the outcome, so keep tracebacks for debug only.
        logger.debug("Fallback curl_cffi fallito per %s", url, exc_info=True)
        raise FeedFetchError(
            url, f"curl_cffi: {exc}", status_code=blocked.status_code
        ) from exc

    if not content:
        raise FeedFetchError(url, "risposta vuota", status_code=200)
    if _looks_like_cloudflare_challenge(content):
        raise FeedFetchError(
            url,
            "Cloudflare JS challenge non superabile senza browser reale. "
            "Prova con un URL diretto del feed RSS.",
            status_code=200,
        )
    return _metadata_result(content, response.headers)


__all__ = [
    "MAX_FEED_BYTES",
    "HttpFetchResult",
    "ResponseTooLargeError",
    "fetch_url_response",
    "read_limited",
]
