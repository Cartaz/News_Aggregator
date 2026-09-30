"""Serializzazione/deserializzazione JSON delle sorgenti feed."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.models import FeedItem, FeedSource

logger = logging.getLogger(__name__)


def serialize_source(source: FeedSource) -> dict[str, Any]:
    return {
        "url": source.url,
        "title": source.title,
        "enabled": source.enabled,
        "last_updated": source.last_updated.isoformat()
        if source.last_updated
        else None,
        "last_error": source.last_error,
        "category": source.category,
        "resolved_feed_url": source.resolved_feed_url,
        "http_etag": source.http_etag,
        "http_last_modified": source.http_last_modified,
        "items": [_serialize_item(it) for it in source.items],
    }


def _serialize_item(item: FeedItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "source_id": item.source_id,
        "title": item.title,
        "link": item.link,
        "summary": item.summary,
        "published": item.published.isoformat(),
        "author": item.author,
        "guid": item.guid,
        "read": item.read,
    }


def deserialize_source(data: dict[str, Any]) -> FeedSource:
    if not isinstance(data, dict):
        raise ValueError("Sorgente non oggetto")
    for name in ("url", "title", "last_error", "category", "resolved_feed_url", "http_etag", "http_last_modified"):
        if name in data and not isinstance(data[name], str):
            raise ValueError(f"{name} non stringa")
    if not data.get("url", "").strip():
        raise ValueError("URL sorgente vuoto")
    if type(data.get("enabled", True)) is not bool:
        raise ValueError("enabled non booleano")
    source = FeedSource(
        url=data["url"],
        title=data.get("title", data["url"]),
        enabled=data.get("enabled", True),
        last_error=data.get("last_error", ""),
        category=data.get("category", ""),
        resolved_feed_url=data.get("resolved_feed_url", ""),
        http_etag=data.get("http_etag", ""),
        http_last_modified=data.get("http_last_modified", ""),
    )
    last_str: str | None = data.get("last_updated")
    if last_str:
        try:
            source.last_updated = _parse_datetime(last_str)
        except (TypeError, ValueError):
            logger.warning("Data aggiornamento non valida per %s", source.url)
            source.last_updated = None
    raw_items = data.get("items", [])
    if not isinstance(raw_items, list):
        logger.warning("Lista articoli non valida per %s", source.url)
        raw_items = []
    for item_data in raw_items:
        try:
            source.items.append(_deserialize_item(item_data, source.id))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Articolo ignorato (dati non validi): %s", exc)
    return source


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    # Older catalogs may contain naive ISO dates. Interpret them consistently
    # as UTC before any age comparison or ordering.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _deserialize_item(data: dict[str, Any], source_id: str) -> FeedItem:
    if not isinstance(data, dict):
        raise ValueError("Articolo non oggetto")
    for name in ("id", "title", "link", "summary", "author", "guid"):
        if name in data and not isinstance(data[name], str):
            raise ValueError(f"{name} articolo non stringa")
    if not data.get("id"):
        raise ValueError("Identità articolo vuota")
    if type(data.get("read", False)) is not bool:
        raise ValueError("read non booleano")
    published = _parse_datetime(data["published"])
    return FeedItem(
        id=data["id"],
        source_id=source_id,
        title=data["title"],
        link=data.get("link", ""),
        summary=data.get("summary", ""),
        published=published,
        author=data.get("author", ""),
        guid=data.get("guid", ""),
        read=data.get("read", False),
    )


__all__ = ["serialize_source", "deserialize_source"]
