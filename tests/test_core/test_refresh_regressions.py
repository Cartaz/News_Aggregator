"""Regression tests for refresh/new-item detection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from config.constants import FeedDefaults
from core.feed_manager import FeedManager
from core.models import FeedItem


@pytest.fixture
def manager(tmp_paths: Path, reset_event_bus: None) -> FeedManager:
    return FeedManager()


def _item(source_id: str, suffix: str, published: datetime) -> FeedItem:
    return FeedItem.from_raw(
        source_id=source_id,
        title=f"Article {suffix}",
        link=f"https://example.com/{suffix}",
        summary="",
        published=published,
    )


def test_stale_feed_entries_are_not_reported_as_new_repeatedly(
    manager: FeedManager,
) -> None:
    """Entries outside the visible age window must never trigger new-item events."""
    source = manager.add("https://example.com/feed.xml")
    now = datetime.now(timezone.utc)
    recent = _item(source.id, "recent", now - timedelta(minutes=5))
    stale = _item(
        source.id,
        "stale",
        now - timedelta(hours=FeedDefaults.MAX_ITEM_AGE_HOURS + 2),
    )

    with patch(
        "core.feed_manager.fetch_and_parse",
        return_value=("Example", [recent, stale]),
    ):
        first_count = manager.refresh(source.id)
        second_count = manager.refresh(source.id)

    assert first_count == 1
    assert second_count == 0
    assert [item.id for item in manager.get(source.id).items] == [recent.id]


def test_stale_only_feed_reports_zero_new_items(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml")
    stale = _item(
        source.id,
        "stale",
        datetime.now(timezone.utc)
        - timedelta(hours=FeedDefaults.MAX_ITEM_AGE_HOURS + 1),
    )

    with patch(
        "core.feed_manager.fetch_and_parse",
        return_value=("Example", [stale]),
    ):
        assert manager.refresh(source.id) == 0

    assert manager.get(source.id).items == []
