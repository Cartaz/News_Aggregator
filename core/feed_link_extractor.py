"""Estrazione link RSS/Atom da pagine HTML.

Usa ``html.parser.HTMLParser`` della libreria standard per parsare i tag
``<link>`` e ``<a>`` in modo robusto, gestendo anche HTML malformato,
attributi in ordine arbitrario, self-closing e virgolette miste. Il modulo
mantiene la logica di estrazione separata dall'orchestrazione HTTP del fetcher.
"""

from __future__ import annotations

import logging
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

MAX_FEED_CANDIDATES = 5

# Tipi MIME che indicano un feed RSS/Atom
RSS_TYPES: frozenset[str] = frozenset({
    "application/rss+xml",
    "application/atom+xml",
    "application/xml",
    "text/xml",
    "application/rss",
})


class _LinkExtractor(HTMLParser):
    """Parser HTML che estrae tag ``<link rel="alternate">`` e ``<a>``.

    Accumula in ``self.feed_links`` gli URL dei feed trovati (standard
    ``<link rel="alternate" type="application/rss+xml" href="...">``).
    Accumula in ``self.anchor_hrefs`` tutti gli href dei tag ``<a>``
    (per fallback successivo).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.feed_links: list[str] = []
        self.anchor_hrefs: list[str] = []
        self._seen_feeds: set[str] = set()

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        """Processa i tag ``<link>`` e ``<a>``."""
        if tag == "link":
            self._handle_link(attrs)
        elif tag == "a":
            self._handle_anchor(attrs)

    def _handle_link(self, attrs: list[tuple[str, str | None]]) -> None:
        """Verifica se un ``<link>`` è un feed RSS/Atom valido."""
        attr_dict: dict[str, str] = {
            k.lower(): (v or "") for k, v in attrs
        }
        rel: str = attr_dict.get("rel", "").lower()
        type_val: str = attr_dict.get("type", "").lower()
        href: str = attr_dict.get("href", "")
        # Standard: rel="alternate" + type="application/rss+xml"
        if rel == "alternate" and type_val in RSS_TYPES and href:
            if href not in self._seen_feeds:
                self.feed_links.append(href)
                self._seen_feeds.add(href)

    def _handle_anchor(self, attrs: list[tuple[str, str | None]]) -> None:
        """Raccoglie tutti gli href dei tag ``<a>`` per fallback."""
        for k, v in attrs:
            if k.lower() == "href" and v:
                self.anchor_hrefs.append(v)
                break


def extract_feed_links(html: bytes, base_url: str) -> list[str]:
    """Estrae gli URL dei feed dichiarati nell'HTML.

    Strategia a 2 livelli:
    1. ``<link rel="alternate" type="application/rss+xml" href="...">``
       (standard), anche verso altri domini (es. FeedBurner).
    2. Fallback: ``<a href>`` che contengono "feed", "rss" o "atom", ma solo
       sullo stesso sito: un link qualsiasi nel footer non deve diventare la
       sorgente dell'utente.

    Solo URL http(s), al massimo ``MAX_FEED_CANDIDATES`` per livello: ogni
    candidato costa una richiesta di rete durante il refresh.
    """
    if not html:
        return []
    # Limita a 512KB per evitare OOM su pagine giganti
    page_text = html[:524288].decode("utf-8", errors="ignore")
    parser = _LinkExtractor()
    try:
        parser.feed(page_text)
        parser.close()
    except Exception as exc:
        logger.warning("Errore parsing HTML per feed discovery: %s", exc)

    declared = _absolute_http_urls(parser.feed_links, base_url)
    if declared:
        return declared[:MAX_FEED_CANDIDATES]

    site = _site_host(base_url)
    anchors = [
        href
        for href in parser.anchor_hrefs
        if "comment" not in href.lower()  # WordPress /comments/feed/
        and any(token in href.lower() for token in ("feed", "rss", "atom"))
    ]
    same_site = [
        url for url in _absolute_http_urls(anchors, base_url) if _site_host(url) == site
    ]
    return same_site[:MAX_FEED_CANDIDATES]


def _absolute_http_urls(hrefs: list[str], base_url: str) -> list[str]:
    result: list[str] = []
    for href in hrefs:
        absolute = urljoin(base_url, href.strip())
        parsed = urlparse(absolute)
        if parsed.scheme in {"http", "https"} and parsed.netloc and absolute not in result:
            result.append(absolute)
    return result


def _site_host(url: str) -> str:
    """Host without a leading ``www.``, used to keep anchor fallbacks on-site."""
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


__all__ = ["MAX_FEED_CANDIDATES", "RSS_TYPES", "extract_feed_links"]
