"""Estrazione link RSS/Atom da pagine HTML.

Usa ``html.parser.HTMLParser`` della libreria standard per parsare i tag
``<link>`` e ``<a>`` in modo robusto, gestendo anche HTML malformato,
attributi in ordine arbitrario, self-closing e virgolette miste. Il modulo
mantiene la logica di estrazione separata dall'orchestrazione HTTP del fetcher.
"""

from __future__ import annotations

import logging
from html.parser import HTMLParser
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

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
       (standard). Tollerante all'ordine degli attributi e ai tipi
       MIME comuni. Usa ``HTMLParser`` per robustezza.
    2. Fallback: ``<a href="...feed...">`` nel body per siti non
       standard (alcuni siti linkano il feed solo nel footer).

    Args:
        html: Bytes dell'HTML.
        base_url: URL della pagina (per risolvere URL relativi).

    Returns:
        Lista di URL assoluti dei feed trovati (deduplicati).
    """
    if not html:
        return []
    # Limita a 512KB per evitare OOM su pagine giganti
    try:
        page_text: str = html[:524288].decode("utf-8", errors="ignore")
    except (UnicodeDecodeError, AttributeError):
        return []
    parser: _LinkExtractor = _LinkExtractor()
    try:
        parser.feed(page_text)
        parser.close()
    except Exception as exc:
        logger.warning("Errore parsing HTML per feed discovery: %s", exc)

    # Risolvi URL relativi e deduplica
    result: list[str] = []
    seen: set[str] = set()
    for href in parser.feed_links:
        absolute: str = urljoin(base_url, href)
        if absolute not in seen:
            result.append(absolute)
            seen.add(absolute)
    if result:
        return result

    # Livello 2 (fallback): cerca <a href="...feed..."> o "...rss..."
    for href in parser.anchor_hrefs:
        href_lower: str = href.lower()
        # Evita link a /comments/feed/ di WordPress (commenti, non articoli)
        if "comment" in href_lower:
            continue
        # Cerca href che contengano "feed", "rss" o "atom"
        if "feed" in href_lower or "rss" in href_lower or "atom" in href_lower:
            absolute = urljoin(base_url, href)
            if absolute not in seen:
                result.append(absolute)
                seen.add(absolute)
    return result


__all__ = ["extract_feed_links", "RSS_TYPES"]
