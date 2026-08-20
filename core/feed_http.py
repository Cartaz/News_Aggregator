"""Strategia di fetch HTTP con fallback ``curl_cffi`` per WAF.

Estratto da ``feed_fetcher.py`` per rispettare il limite di 300 righe
per file (§5.1.3). Implementa la strategia:

1. Prima prova ``requests`` (veloce, leggera).
2. Se 403 o XML mal formato, riprova con ``curl_cffi`` impersonando
   Chrome 121. Questo bypassa i WAF Cloudflare/Akamai che bloccano
   i client Python noti.
3. Se anche ``curl_cffi`` fallisce, solleva l'errore originale.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from requests.exceptions import RequestException, Timeout

from config.constants import FeedDefaults
from core.exceptions import FeedFetchError

logger = logging.getLogger(__name__)

# Lazy import di curl_cffi (non sempre disponibile in test)
try:
    from curl_cffi import requests as cf_requests  # type: ignore[import-untyped]
    _HAS_CURL_CFFI: bool = True
except ImportError:
    cf_requests = None  # type: ignore[assignment]
    _HAS_CURL_CFFI = False

# Verifica disponibilità brotli: necessario per decomprimere risposte
# `Content-Encoding: br`. Senza, i byte compressi vengono passati
# direttamente a feedparser che fallisce con "not well-formed".
try:
    import brotli  # noqa: F401  (l'import basta per abilitare urllib3)
    _HAS_BROTLI: bool = True
except ImportError:
    _HAS_BROTLI = False


def _accept_encoding_value() -> str:
    """Restituisce l'header Accept-Encoding adatto all'ambiente.

    Se brotli è installato, includiamo `br` (molti siti lo usano e
    riduce la banda del 60-80% rispetto a gzip). Se NON è installato,
    NON includiamo `br`: altrimenti il server invia byte brotli che
    requests non sa decomprimere e feedparser riceve byte binari grezzi.
    """
    if _HAS_BROTLI:
        return "gzip, deflate, br"
    logger.debug(
        "brotli non installato: Accept-Encoding senza 'br'. "
        "Installa il pacchetto 'Brotli' per supporto completo."
    )
    return "gzip, deflate"


def _browser_headers() -> dict[str, str]:
    """Header HTTP browser-like completi."""
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


def _looks_like_cloudflare_challenge(content: bytes) -> bool:
    """Rileva la pagina challenge HTML di Cloudflare ('Just a moment...').

    Cloudflare serve questa pagina con 200/403 quando la richiesta
    supera il fingerprint check ma non la JS challenge. curl_cffi
    supera il fingerprint, ma la JS challenge richiede un browser
    reale. Rileviamo questo caso per dare un messaggio d'errore utile.
    """
    if not content:
        return False
    head: bytes = content[:2048].lower()
    return b"just a moment" in head or b"cf-browser-verification" in head


def fetch_url(url: str, timeout: int | None = None) -> bytes:
    """Scarica il contenuto di un URL con fallback ``curl_cffi``.

    Strategia:
    1. ``requests.get`` con header browser-like.
    2. Se 403 o risposta vuota, riprova con ``curl_cffi`` impersonando
       Chrome 121 (bypassa WAF Cloudflare basilari).
    3. Se ``curl_cffi`` non è disponibile o fallisce, solleva
       ``FeedFetchError`` con il messaggio appropriato.

    Args:
        url: URL da scaricare.
        timeout: Timeout in secondi (default da FeedDefaults).

    Returns:
        I bytes del contenuto scaricato.

    Raises:
        FeedFetchError: Se entrambi i metodi falliscono.
    """
    actual_timeout: int = timeout or FeedDefaults.REQUEST_TIMEOUT_SECONDS
    last_error: FeedFetchError | None = None

    # Tentativo 1: requests
    try:
        logger.debug("GET %s (requests, timeout=%ds)", url, actual_timeout)
        response: requests.Response = requests.get(
            url,
            timeout=actual_timeout,
            headers=_browser_headers(),
            allow_redirects=True,
        )
        response.raise_for_status()
        if response.content:
            # Sanity check: se la risposta è brotli ma brotli non è
            # installato, i byte sono illeggibili. Avvisa l'utente.
            ce = response.headers.get("Content-Encoding", "").lower()
            if "br" in ce and not _HAS_BROTLI:
                logger.warning(
                    "Risposta brotli da %s ma brotli non installato — "
                    "i byte saranno probabilmente illeggibili. "
                    "Installa 'Brotli' (pip install Brotli).",
                    url,
                )
            return response.content
        # Contenuto vuoto: prova curl_cffi
        last_error = FeedFetchError(url, "risposta vuota")
    except requests.HTTPError as exc:
        status: int = response.status_code
        if status == 403:
            last_error = FeedFetchError(
                url,
                "403 Forbidden — WAF blocca requests, provo curl_cffi",
            )
        else:
            last_error = FeedFetchError(url, str(exc))
    except Timeout as exc:
        last_error = FeedFetchError(url, f"timeout ({actual_timeout}s)")
    except RequestException as exc:
        last_error = FeedFetchError(url, str(exc))

    # Tentativo 2: curl_cffi (se disponibile)
    if _HAS_CURL_CFFI:
        try:
            logger.debug("GET %s (curl_cffi, chrome120)", url)
            cf_response: Any = cf_requests.get(
                url,
                impersonate="chrome120",
                timeout=actual_timeout,
                allow_redirects=True,
            )
            if cf_response.status_code == 200 and cf_response.content:
                content_bytes: bytes = bytes(cf_response.content)
                # curl_cffi decomprime brotli nativamente, ma se la
                # risposta è la challenge page di Cloudflare, segnaliamolo
                # con un errore chiaro invece di passare HTML al parser.
                if _looks_like_cloudflare_challenge(content_bytes):
                    raise FeedFetchError(
                        url,
                        "Cloudflare JS challenge non superabile senza "
                        "browser reale. Prova con un URL diretto del "
                        "feed RSS o un proxy (es. rss-bridge).",
                    )
                return content_bytes
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
        except FeedFetchError:
            raise
        except Exception as exc:
            logger.debug("curl_cffi fallito: %s", exc)
            # Mantieni last_error dal tentativo requests

    raise last_error or FeedFetchError(url, "errore sconosciuto")


def fetch_url_simple(url: str, timeout: int) -> bytes:
    """Scarica un URL con solo ``requests`` (no fallback).

    Usato per i path fallback dell'auto-discovery, dove curl_cffi
    non serve (sono path diretti di feed).

    Args:
        url: URL da scaricare.
        timeout: Timeout in secondi.

    Returns:
        I bytes del contenuto.

    Raises:
        FeedFetchError: Se la richiesta fallisce.
    """
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


__all__ = ["fetch_url", "fetch_url_simple"]
