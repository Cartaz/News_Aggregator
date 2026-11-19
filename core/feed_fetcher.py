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

    Se ``url`` è una pagina HTML, prova prima i feed che dichiara e poi i
    percorsi convenzionali. Un errore di trasporto (rete giù, timeout) non
    avvia la discovery: ogni candidato fallirebbe allo stesso modo.
    """
    actual_timeout: int = timeout or FeedDefaults.REQUEST_TIMEOUT_SECONDS

    _raise_if_cancelled(cancel_event)
    try:
        response = fetch_url_response(
            url,
            actual_timeout,
            etag=etag,
            last_modified=last_modified,
            cancel_event=cancel_event,
        )
    except FeedFetchError as exc:
        if exc.is_transient or _is_feed_url(url):
            raise
        logger.debug("Fetch iniziale fallito per %s, provo i percorsi noti: %s", url, exc)
        return _try_candidates(
            candidate_feed_urls(url), source_id, actual_timeout, cancel_event, exc
        )

    _raise_if_cancelled(cancel_event)
    if response.not_modified or _looks_like_xml(response.content):
        return _result_from_http(response, source_id, url)

    candidates = extract_feed_links(response.content, url)
    if not _is_feed_url(url):
        candidates += [
            candidate for candidate in candidate_feed_urls(url) if candidate not in candidates
        ]
    return _try_candidates(
        candidates,
        source_id,
        actual_timeout,
        cancel_event,
        FeedParseError(
            url,
            "contenuto non è un feed RSS/Atom né una pagina HTML con link "
            "a un feed. Verifica che l'URL sia corretto.",
        ),
    )


def _try_candidates(
    candidates: list[str],
    source_id: str,
    timeout: int,
    cancel_event: threading.Event | None,
    failure: FeedFetchError | FeedParseError,
) -> FeedFetchResult:
    """Return the first candidate that is a real feed, else raise ``failure``."""
    for candidate in candidates:
        _raise_if_cancelled(cancel_event)
        logger.info("Auto-discovery: provo %s", candidate)
        try:
            result = _fetch_candidate(
                candidate, source_id, timeout, cancel_event=cancel_event
            )
        except FeedFetchError as exc:
            if exc.is_transient:
                # The network went away mid-discovery: stop instead of
                # waiting out one timeout per remaining candidate.
                raise
            logger.debug("Candidato %s non utilizzabile: %s", candidate, exc)
            continue
        except FeedParseError as exc:
            logger.debug("Candidato %s non utilizzabile: %s", candidate, exc)
            continue
        logger.info("Auto-discovery: feed trovato a %s", candidate)
        return result
    raise failure


def _fetch_candidate(
    url: str,
    source_id: str,
    timeout: int,
    *,
    cancel_event: threading.Event | None = None,
) -> FeedFetchResult:
    """Scarica e analizza un URL candidato che deve essere direttamente un feed."""
    _raise_if_cancelled(cancel_event)
    response = fetch_url_response(url, timeout, cancel_event=cancel_event)
    _raise_if_cancelled(cancel_event)
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
    "fetch_and_parse_resolved",
]
