"""Compatibility wrappers for feed write operations.

Mutation ownership lives in ``FeedManager``. These functions remain only for
callers using the previous helper API and deliberately contain no business
rules, persistence handling or event dispatch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.models import FeedSource

if TYPE_CHECKING:
    from core.feed_manager import FeedManager


def rename_feed(
    manager: "FeedManager", source_id: str, new_title: str
) -> FeedSource:
    return manager.rename_feed(source_id, new_title)


def set_category(
    manager: "FeedManager", source_id: str, category: str
) -> FeedSource:
    return manager.set_category(source_id, category)


__all__ = ["rename_feed", "set_category"]
