"""Recupero feed via HTTP, auto-discovery e parsing del contenuto.

Usa ``fetch_url`` (con fallback ``curl_cffi``) per il download, e
``feed_link_extractor`` per l'auto-discovery dei feed RSS/Atom da
pagine HTML. Framework-agnostic: solleva ``FeedError``.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from config.constants import FeedDefaults
from core.exceptions import FeedFetchError, FeedParseError
from core.feed_http import fetch_url
from core.feed_link_extractor import extract_feed_links
from core.feed_parser import parse_feed_bytes
from core.models import FeedItem

logger = logging.getLogger(__name__)

_XML_SNIFF_PREFIX: bytes = b"<?xml"
_XML_ROOT_TAGS: tuple[bytes, ...] = (b"<rss", b"<feed", b"<rdf:RDF")

_KNOWN_FEED_OVERRIDES: dict[str, list[str]] = {
    "www.bloomberg.com": [
        "https://feeds.bloomberg.com/news.rss",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.bloomberg.com/technology/news.rss",
        "https://feeds.bloomberg.com/politics/news.rss",
        "https://feeds.bloomberg.com/economics/news.rss",
        "https://feeds.bloomberg.com/business/news.rss",
    ],
    "www.economist.com": [
        "https://www.economist.com/leaders/rss.xml",
        "https://www.economist.com/briefing/rss.xml",
        "https://www.economist.com/the-world-this-week/rss.xml",
        "https://www.economist.com/finance-and-economics/rss.xml",
        "https://www.economist.com/business/rss.xml",
        "https://www.economist.com/science-and-technology/rss.xml",
        "https://www.economist.com/the-economist-explains/rss.xml",
    ],
}


def _looks_like_xml(content: bytes) -> bool:
    """Verifica se il contenuto appare essere XML (RSS/Atom)."""
    if not content:
        return False
    head: bytes = content[:500].lstrip()
    if head.startswith(_XML_SNIFF_PREFIX):
        return True
    return any(tag in head for tag in _XML_ROOT_TAGS)


def _looks_like_html(content: bytes) -> bool:
    """Verifica se il contenuto appare essere HTML."""
    if not content:
        return False
    head: bytes = content[:500].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def _is_feed_url(url: str) -> bool:
    """Verifica se l'URL ha un'estensione che suggerisce un feed."""
    path: str = urlparse(url).path.lower()
    return any(
        path.endswith(ext)
        for ext in (".xml", ".rss", ".atom", "/feed", "/rss", "/feed/")
    )


def fetch_and_parse(
    url: str, source_id: str, timeout: int | None = None
) -> tuple[str, list[FeedItem]]:
    """API compatibile: recupera un feed e restituisce titolo + articoli."""
    title, items, _resolved_url = fetch_and_parse_resolved(
        url, source_id, timeout
    )
    return title, items


def fetch_and_parse_resolved(
    url: str, source_id: str, timeout: int | None = None
) -> tuple[str, list[FeedItem], str]:
    """Recupera un feed e restituisce anche l'URL RSS/Atom effettivo.

    ``resolved_url`` coincide con ``url`` quando l'URL fornito è già un feed;
    se invece ``url`` è una homepage o una pagina HTML, contiene l'URL trovato
    tramite auto-discovery/fallback. Questo permette al chiamante di salvarlo
    come cache ed evitare di ripetere la discovery ai refresh successivi.
    """
    actual_timeout: int = timeout or FeedDefaults.REQUEST_TIMEOUT_SECONDS

    content: bytes = b""
    fetch_failed: bool = False
    try:
        content = fetch_url(url, actual_timeout)
    except FeedFetchError as exc:
        logger.debug(
            "Fetch iniziale fallito per %s, provo path fallback: %s",
            url,
            exc,
        )
        fetch_failed = True

    if not fetch_failed:
        if not content:
            raise FeedFetchError(url, "risposta vuota")

        final_url: str = url

        if _looks_like_xml(content):
            logger.debug("Contenuto rilevato come XML, parsing diretto")
            title, items = parse_feed_bytes(content, source_id, final_url)
            return title, items, final_url

        feed_urls: list[str] = extract_feed_links(content, final_url)
        if feed_urls:
            logger.info(
                "Auto-discovery: trovati %d feed in %s, provo %s",
                len(feed_urls),
                final_url,
                feed_urls[0],
            )
            return _fetch_feed_recursive(
                feed_urls[0], source_id, actual_timeout
            )

        if not _is_feed_url(final_url):
            candidates: list[str] = _guess_feed_paths(final_url)
            for candidate in candidates:
                logger.info("Auto-discovery fallback: provo path %s", candidate)
                try:
                    result = _fetch_feed_recursive(
                        candidate, source_id, actual_timeout
                    )
                    logger.info("Auto-discovery: feed trovato a %s", candidate)
                    return result
                except (FeedFetchError, FeedParseError) as exc:
                    logger.debug("Fallback path %s fallito: %s", candidate, exc)
                    continue

        raise FeedParseError(
            final_url,
            "contenuto non è un feed RSS/Atom né una pagina HTML con link "
            "a un feed. Verifica che l'URL sia corretto.",
        )

    if not _is_feed_url(url):
        candidates = _guess_feed_paths(url)
        last_exc: FeedFetchError | FeedParseError | None = None
        for candidate in candidates:
            logger.info(
                "Auto-discovery fallback (fetch fallito): provo %s", candidate
            )
            try:
                result = _fetch_feed_recursive(
                    candidate, source_id, actual_timeout
                )
                logger.info("Auto-discovery: feed trovato a %s", candidate)
                return result
            except (FeedFetchError, FeedParseError) as exc:
                logger.debug("Fallback path %s fallito: %s", candidate, exc)
                last_exc = exc
                continue
        if last_exc is not None:
            raise last_exc

    raise FeedFetchError(
        url,
        "URL principale non raggiungibile e nessun path fallback "
        "disponibile. Verifica l'URL o inseriscine uno diretto al feed.",
    )


def _fetch_feed_recursive(
    url: str, source_id: str, timeout: int
) -> tuple[str, list[FeedItem], str]:
    """Scarica e analizza un URL che si presume essere un feed."""
    content: bytes = fetch_url(url, timeout)
    if not content:
        raise FeedFetchError(url, "risposta vuota")
    if _looks_like_html(content):
        raise FeedParseError(
            url,
            "il server ha risposto con HTML, non con un feed RSS/Atom. "
            "Possibile causa: WAF/bot-detection che serve una challenge "
            "page, oppure l'URL non punta a un feed reale.",
        )
    title, items = parse_feed_bytes(content, source_id, url)
    return title, items, url


def _guess_feed_paths(base_url: str) -> list[str]:
    """Genera una lista di URL di feed plausibili da un URL base."""
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return []

    standard_paths: list[str] = []
    if not parsed.path or parsed.path == "/" or parsed.path == "":
        base = f"{parsed.scheme}://{parsed.netloc}"
        standard_paths = [
            f"{base}/rss.xml",
            f"{base}/feed/",
            f"{base}/feed.xml",
            f"{base}/feeds.xml",
            f"{base}/rss",
            f"{base}/atom.xml",
            f"{base}/index.xml",
        ]

    overrides: list[str] = _KNOWN_FEED_OVERRIDES.get(parsed.netloc.lower(), [])
    return standard_paths + overrides


__all__ = ["fetch_and_parse", "fetch_and_parse_resolved"]
