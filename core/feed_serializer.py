"""Serializzazione/deserializzazione JSON delle sorgenti feed."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from core.models import FeedItem, FeedSource

logger = logging.getLogger(__name__)


def serialize_source(source: FeedSource) -> dict[str, Any]:
    """Serializza una ``FeedSource`` in dict JSON-compatibile."""
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
        "read": item.read,
    }


def deserialize_source(data: dict[str, Any]) -> FeedSource:
    """Deserializza una sorgente mantenendo compatibilità con vecchi JSON."""
    source: FeedSource = FeedSource(
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
            source.last_updated = datetime.fromisoformat(last_str)
        except ValueError:
            source.last_updated = None
    for item_data in data.get("items", []):
        try:
            source.items.append(_deserialize_item(item_data))
        except (KeyError, ValueError) as exc:
            logger.warning("Articolo ignorato (dati non validi): %s", exc)
    return source


def _deserialize_item(data: dict[str, Any]) -> FeedItem:
    published: datetime = datetime.fromisoformat(data["published"])
    return FeedItem(
        id=data["id"],
        source_id=data["source_id"],
        title=data["title"],
        link=data["link"],
        summary=data["summary"],
        published=published,
        author=data.get("author", ""),
        read=data.get("read", False),
    )


__all__ = ["serialize_source", "deserialize_source"]
