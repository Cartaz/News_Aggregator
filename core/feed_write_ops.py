"""Focused write operations exposed through ``FeedManager``'s public API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.event_bus import EventBus
from core.exceptions import FeedError
from core.models import FeedSource

if TYPE_CHECKING:
    from core.feed_manager import FeedManager

logger = logging.getLogger(__name__)


def rename_feed(
    manager: "FeedManager", source_id: str, new_title: str
) -> FeedSource:
    """Rename a feed without depending on ``FeedManager`` private storage."""
    cleaned = (new_title or "").strip()
    if not cleaned:
        raise FeedError("Il nuovo titolo non può essere vuoto")

    source = manager.get(source_id)
    source.title = cleaned
    manager.save()
    EventBus().emit(
        "feed_renamed",
        {"source_id": source_id, "new_title": cleaned},
    )
    logger.info("Feed %s rinominato in %r", source_id, cleaned)
    return source


def set_category(
    manager: "FeedManager", source_id: str, category: str
) -> FeedSource:
    """Assign or clear a category through the manager's public surface."""
    cleaned = (category or "").strip()
    source = manager.get(source_id)
    source.category = cleaned
    manager.save()
    EventBus().emit(
        "feed_category_changed",
        {"source_id": source_id, "category": cleaned},
    )
    logger.info(
        "Feed %s assegnato a categoria %r",
        source_id,
        cleaned or "(nessuna)",
    )
    return source


__all__ = ["rename_feed", "set_category"]
