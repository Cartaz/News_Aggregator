"""Parser per feed RSS 2.0 e Atom 1.0.

Usa ``feedparser`` per l'analisi strutturale e ``BeautifulSoup`` per la
pulizia dell'HTML dal sommario. Il risultato è testo puro, senza
immagini embed né pubblicità inline.

Questo modulo è framework-agnostic: non importa da ``ui/`` né da Qt.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

import feedparser
from feedparser.util import FeedParserDict

from config.constants import FeedDefaults
from core.exceptions import FeedParseError
from core.models import FeedItem

logger = logging.getLogger(__name__)


class _HTMLStripper(HTMLParser):
    """Parser HTML minimale che estrae solo il testo."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        """Accumula i testi ignorando tag e attributi."""
        self._chunks.append(data)

    def get_text(self) -> str:
        """Restituisce il testo accumulato, normalizzato."""
        text: str = " ".join(self._chunks)
        return " ".join(text.split())


def strip_html(html_text: str) -> str:
    """Rimuove tutti i tag HTML dal testo.

    Args:
        html_text: Stringa con tag HTML.

    Returns:
        Testo puro con spaziatura normalizzata.
    """
    if not html_text:
        return ""
    stripper: _HTMLStripper = _HTMLStripper()
    stripper.feed(html_text)
    return stripper.get_text().strip()


def truncate(text: str, max_length: int) -> str:
    """Tronca il testo aggiungendo ellissi se supera la lunghezza."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 1].rstrip() + "\u2026"


def _parse_date(entry: FeedParserDict) -> datetime:
    """Estrae la data di pubblicazione come datetime timezone-aware."""
    for field_name in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed: Any = entry.get(field_name)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return datetime.now(timezone.utc)


def _extract_summary(entry: FeedParserDict) -> str:
    """Estrae e pulisce il sommario dell'articolo."""
    raw: str = entry.get("summary") or entry.get("description") or ""
    cleaned: str = strip_html(raw)
    return truncate(cleaned, FeedDefaults.MAX_SUMMARY_LENGTH)


def parse_feed_bytes(
    content: bytes, source_id: str, url: str
) -> tuple[str, list[FeedItem]]:
    """Analizza il contenuto di un feed RSS/Atom.

    Args:
        content: Bytes grezzi del feed.
        source_id: ID del feed di appartenenza.
        url: URL del feed (per messaggi di errore).

    Returns:
        Tupla (titolo_feed, lista_articoli).

    Raises:
        FeedParseError: Se il contenuto non è un feed valido o è vuoto.
    """
    if not content:
        raise FeedParseError(url, "contenuto vuoto")

    # feedparser è tollerante: estrae entries anche da XML malformato
    # (BOM, newline iniziale, dichiarazione XML non al primo byte, ecc.).
    # Usiamo parse() con response_headers=False per evitare warning.
    parsed: FeedParserDict = feedparser.parse(content)
    # Se non ci sono entries, è un vero errore di parsing
    if not parsed.entries:
        bozo_exc = parsed.get("bozo_exception", "unknown parser error")
        raise FeedParseError(url, str(bozo_exc))

    feed_title: str = parsed.feed.get("title", url) or url
    items: list[FeedItem] = []

    for entry in parsed.entries[:FeedDefaults.MAX_ITEMS_PER_FEED]:
        title: str = strip_html(entry.get("title", "")).strip() or "(senza titolo)"
        link: str = entry.get("link", "").strip()
        if not link:
            continue
        published: datetime = _parse_date(entry)
        summary: str = _extract_summary(entry)
        author: str = strip_html(entry.get("author", "")).strip()
        items.append(
            FeedItem.from_raw(
                source_id=source_id,
                title=title,
                link=link,
                summary=summary,
                published=published,
                author=author,
            )
        )

    logger.info("Feed %s parsato: %d articoli", url, len(items))
    return feed_title, items


__all__ = ["parse_feed_bytes", "strip_html", "truncate"]
