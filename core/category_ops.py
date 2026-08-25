"""Read-only category and aggregate-feed queries.

These helpers depend only on the public ``FeedManager`` interface. Locking and
storage representation remain owned by ``FeedManager`` instead of leaking into
query modules.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from config.constants import FeedDefaults
from core.models import FeedItem, FeedSource

if TYPE_CHECKING:
    from core.feed_manager import FeedManager


def _age_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(
        hours=FeedDefaults.MAX_ITEM_AGE_HOURS
    )


def list_categories(manager: "FeedManager") -> list[str]:
    """Return the category names currently assigned to feeds."""
    return sorted({source.category for source in manager.get_all() if source.category})


def get_feeds_by_category(
    manager: "FeedManager", category: str
) -> list[FeedSource]:
    """Return feeds assigned to ``category``."""
    return [source for source in manager.get_all() if source.category == category]


def get_items_by_category(
    manager: "FeedManager", category: str, limit: int = 200
) -> list[FeedItem]:
    """Return recent items from all feeds assigned to ``category``."""
    cutoff = _age_cutoff()
    items = [
        item
        for source in manager.get_all()
        if source.category == category
        for item in source.items
        if item.published >= cutoff
    ]
    items.sort(key=lambda item: item.published, reverse=True)
    return items[:limit]


def get_all_items(
    manager: "FeedManager", limit: int = 200
) -> list[FeedItem]:
    """Return recent items across all feeds, newest first."""
    cutoff = _age_cutoff()
    items = [
        item
        for source in manager.get_all()
        for item in source.items
        if item.published >= cutoff
    ]
    items.sort(key=lambda item: item.published, reverse=True)
    return items[:limit]


__all__ = [
    "list_categories",
    "get_feeds_by_category",
    "get_items_by_category",
    "get_all_items",
]
