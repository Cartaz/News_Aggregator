"""Parser per feed RSS 2.0 e Atom 1.0."""

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
        self._chunks.append(data)

    def get_text(self) -> str:
        text = " ".join(self._chunks)
        return " ".join(text.split())


def strip_html(html_text: str) -> str:
    if not html_text:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(html_text)
    return stripper.get_text().strip()


def truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - 1].rstrip() + "\u2026"


def _parse_date(entry: FeedParserDict) -> datetime:
    for field_name in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed: Any = entry.get(field_name)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return datetime.now(timezone.utc)


def _has_stable_date(entry: FeedParserDict) -> bool:
    return any(
        entry.get(field_name)
        for field_name in ("published_parsed", "updated_parsed", "created_parsed")
    )


def _extract_summary(entry: FeedParserDict) -> str:
    raw = entry.get("summary") or entry.get("description") or ""
    cleaned = strip_html(raw)
    return truncate(cleaned, FeedDefaults.MAX_SUMMARY_LENGTH)


def _extract_guid(entry: FeedParserDict) -> str:
    """feedparser espone sia RSS guid sia Atom id principalmente come `id`."""
    value = entry.get("id") or entry.get("guid") or ""
    return str(value).strip()


def parse_feed_bytes(
    content: bytes, source_id: str, url: str
) -> tuple[str, list[FeedItem]]:
    """Analizza RSS/Atom e restituisce item già deduplicati per identità."""
    if not content:
        raise FeedParseError(url, "contenuto vuoto")

    parsed: FeedParserDict = feedparser.parse(content)
    if not parsed.entries:
        bozo_exc = parsed.get("bozo_exception", "unknown parser error")
        raise FeedParseError(url, str(bozo_exc))

    feed_title = parsed.feed.get("title", url) or url
    items: list[FeedItem] = []
    seen_ids: set[str] = set()

    for entry in parsed.entries[:FeedDefaults.MAX_ITEMS_PER_FEED]:
        title = strip_html(entry.get("title", "")).strip() or "(senza titolo)"
        link = str(entry.get("link", "") or "").strip()
        guid = _extract_guid(entry)
        # Un item senza GUID/link e senza una data reale non ha un'identità
        # ripetibile: usare datetime.now() lo renderebbe "nuovo" a ogni refresh.
        if not link and not guid and not _has_stable_date(entry):
            continue
        published = _parse_date(entry)
        item = FeedItem.from_raw(
            source_id=source_id,
            title=title,
            link=link,
            summary=_extract_summary(entry),
            published=published,
            author=strip_html(entry.get("author", "")).strip(),
            guid=guid,
        )
        if item.id in seen_ids:
            continue
        seen_ids.add(item.id)
        items.append(item)

    if not items:
        raise FeedParseError(url, "feed senza articoli con identità stabile")

    logger.info("Feed %s parsato: %d articoli", url, len(items))
    return feed_title, items


__all__ = ["parse_feed_bytes", "strip_html", "truncate"]
