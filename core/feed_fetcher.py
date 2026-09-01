"""Recupero feed via HTTP, auto-discovery, cache validation e parsing."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from urllib.parse import urlparse

from config.constants import FeedDefaults
from core.exceptions import FeedFetchError, FeedParseError, RefreshCancelledError
from core.feed_discovery import candidate_feed_urls
from core.feed_http import HttpFetchResult, fetch_url_response
from core.feed_link_extractor import extract_feed_links
from core.feed_parser import parse_feed_bytes
from core.models import FeedItem

logger = logging.getLogger(__name__)

_XML_SNIFF_PREFIX: bytes = b"<?xml"
_XML_ROOT_TAGS: tuple[bytes, ...] = (b"<rss", b"<feed", b"<rdf:RDF")


@dataclass(frozen=True)
class FeedFetchResult:
    """Feed parsato più URL effettivo e metadata HTTP."""

    title: str
    items: list[FeedItem]
    resolved_url: str
    etag: str = ""
    last_modified: str = ""
    not_modified: bool = False

    def __iter__(self):  # type: ignore[no-untyped-def]
        """Mantiene compatibilità con il vecchio unpacking a tre valori."""
        yield self.title
        yield self.items
        yield self.resolved_url


def _raise_if_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise RefreshCancelledError()


def _looks_like_xml(content: bytes) -> bool:
    if not content:
        return False
    head: bytes = content[:500].lstrip()
    if head.startswith(_XML_SNIFF_PREFIX):
        return True
    return any(tag in head for tag in _XML_ROOT_TAGS)


def _looks_like_html(content: bytes) -> bool:
    if not content:
        return False
    head: bytes = content[:500].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def _is_feed_url(url: str) -> bool:
    path: str = urlparse(url).path.lower()
    return any(
        path.endswith(ext)
        for ext in (".xml", ".rss", ".atom", "/feed", "/rss", "/feed/")
    )


def _result_from_http(
    response: HttpFetchResult,
    source_id: str,
    resolved_url: str,
) -> FeedFetchResult:
    if response.not_modified:
        return FeedFetchResult(
            title="",
            items=[],
            resolved_url=resolved_url,
            etag=response.etag,
            last_modified=response.last_modified,
            not_modified=True,
        )
    title, items = parse_feed_bytes(response.content, source_id, resolved_url)
    return FeedFetchResult(
        title=title,
        items=items,
        resolved_url=resolved_url,
        etag=response.etag,
        last_modified=response.last_modified,
    )


def fetch_and_parse(
    url: str, source_id: str, timeout: int | None = None
) -> tuple[str, list[FeedItem]]:
    """API compatibile: recupera un feed e restituisce titolo + articoli."""
    result = fetch_and_parse_resolved(url, source_id, timeout)
    return result.title, result.items


def fetch_and_parse_resolved(
    url: str,
    source_id: str,
    timeout: int | None = None,
    *,
    etag: str = "",
    last_modified: str = "",
    cancel_event: threading.Event | None = None,
) -> FeedFetchResult:
    """Recupera un feed includendo URL risolto e validator HTTP.

    I validator vanno passati solo quando ``url`` è già il feed effettivo
    (URL diretto o ``resolved_feed_url`` cached). Se il server risponde 304,
    il risultato ha ``not_modified=True`` e non viene eseguito il parsing.
    """
    actual_timeout: int = timeout or FeedDefaults.REQUEST_TIMEOUT_SECONDS

    _raise_if_cancelled(cancel_event)
    response: HttpFetchResult | None = None
    fetch_failed = False
    try:
        if cancel_event is None:
            response = fetch_url_response(
                url,
                actual_timeout,
                etag=etag,
                last_modified=last_modified,
            )
        else:
            response = fetch_url_response(
                url,
                actual_timeout,
                etag=etag,
                last_modified=last_modified,
                cancel_event=cancel_event,
            )
    except RefreshCancelledError:
        raise
    except FeedFetchError as exc:
        logger.debug(
            "Fetch iniziale fallito per %s, provo path fallback: %s",
            url,
            exc,
        )
        fetch_failed = True

    _raise_if_cancelled(cancel_event)
    if not fetch_failed and response is not None:
        if response.not_modified:
            return FeedFetchResult(
                title="",
                items=[],
                resolved_url=url,
                etag=response.etag,
                last_modified=response.last_modified,
                not_modified=True,
            )
        content = response.content
        if not content:
            raise FeedFetchError(url, "risposta vuota")

        if _looks_like_xml(content):
            logger.debug("Contenuto rilevato come XML, parsing diretto")
            return _result_from_http(response, source_id, url)

        feed_urls: list[str] = extract_feed_links(content, url)
        if feed_urls:
            logger.info(
                "Auto-discovery: trovati %d feed in %s, provo %s",
                len(feed_urls),
                url,
                feed_urls[0],
            )
            return _fetch_feed_recursive(
                feed_urls[0],
                source_id,
                actual_timeout,
                cancel_event=cancel_event,
            )

        if not _is_feed_url(url):
            for candidate in candidate_feed_urls(url):
                _raise_if_cancelled(cancel_event)
                logger.info("Auto-discovery fallback: provo path %s", candidate)
                try:
                    result = _fetch_feed_recursive(
                        candidate,
                        source_id,
                        actual_timeout,
                        cancel_event=cancel_event,
                    )
                    logger.info("Auto-discovery: feed trovato a %s", candidate)
                    return result
                except RefreshCancelledError:
                    raise
                except (FeedFetchError, FeedParseError) as exc:
                    logger.debug("Fallback path %s fallito: %s", candidate, exc)

        raise FeedParseError(
            url,
            "contenuto non è un feed RSS/Atom né una pagina HTML con link "
            "a un feed. Verifica che l'URL sia corretto.",
        )

    if not _is_feed_url(url):
        last_exc: FeedFetchError | FeedParseError | None = None
        for candidate in candidate_feed_urls(url):
            _raise_if_cancelled(cancel_event)
            logger.info(
                "Auto-discovery fallback (fetch fallito): provo %s", candidate
            )
            try:
                result = _fetch_feed_recursive(
                    candidate,
                    source_id,
                    actual_timeout,
                    cancel_event=cancel_event,
                )
                logger.info("Auto-discovery: feed trovato a %s", candidate)
                return result
            except RefreshCancelledError:
                raise
            except (FeedFetchError, FeedParseError) as exc:
                logger.debug("Fallback path %s fallito: %s", candidate, exc)
                last_exc = exc
        if last_exc is not None:
            raise last_exc

    _raise_if_cancelled(cancel_event)
    raise FeedFetchError(
        url,
        "URL principale non raggiungibile e nessun path fallback "
        "disponibile. Verifica l'URL o inseriscine uno diretto al feed.",
    )


def _fetch_feed_recursive(
    url: str,
    source_id: str,
    timeout: int,
    *,
    etag: str = "",
    last_modified: str = "",
    cancel_event: threading.Event | None = None,
) -> FeedFetchResult:
    """Scarica e analizza un URL che si presume essere un feed."""
    _raise_if_cancelled(cancel_event)
    if cancel_event is None:
        response = fetch_url_response(
            url,
            timeout,
            etag=etag,
            last_modified=last_modified,
        )
    else:
        response = fetch_url_response(
            url,
            timeout,
            etag=etag,
            last_modified=last_modified,
            cancel_event=cancel_event,
        )
    _raise_if_cancelled(cancel_event)
    if response.not_modified:
        return FeedFetchResult(
            title="",
            items=[],
            resolved_url=url,
            etag=response.etag,
            last_modified=response.last_modified,
            not_modified=True,
        )
    if not response.content:
        raise FeedFetchError(url, "risposta vuota")
    if _looks_like_html(response.content):
        raise FeedParseError(
            url,
            "il server ha risposto con HTML, non con un feed RSS/Atom. "
            "Possibile causa: WAF/bot-detection che serve una challenge "
            "page, oppure l'URL non punta a un feed reale.",
        )
    return _result_from_http(response, source_id, url)


__all__ = [
    "FeedFetchResult",
    "fetch_and_parse",
    "fetch_and_parse_resolved",
]
