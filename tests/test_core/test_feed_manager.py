"""Test per core/feed_manager.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.exceptions import FeedDuplicateError, FeedError, FeedNotFoundError
from core.feed_manager import FeedManager


@pytest.fixture
def manager(tmp_paths: Path, reset_event_bus: None) -> FeedManager:
    """Restituisce un FeedManager con storage temporaneo."""
    FeedManager._instance = None  # type: ignore[attr-defined]
    return FeedManager()


def test_add_feed(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml")
    assert source.url == "https://example.com/feed.xml"
    assert source.id
    assert source in manager.get_all()


def test_add_duplicate_raises(manager: FeedManager) -> None:
    manager.add("https://example.com/feed.xml")
    with pytest.raises(FeedDuplicateError):
        manager.add("https://example.com/feed.xml")


def test_add_empty_url_raises(manager: FeedManager) -> None:
    with pytest.raises(FeedError):
        manager.add("   ")


def test_remove_feed(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml")
    manager.remove(source.id)
    assert source not in manager.get_all()


def test_remove_unknown_raises(manager: FeedManager) -> None:
    with pytest.raises(FeedNotFoundError):
        manager.remove("nonexistent_id")


def test_get_unknown_raises(manager: FeedManager) -> None:
    with pytest.raises(FeedNotFoundError):
        manager.get("nonexistent_id")


def test_persistence(tmp_paths: Path, reset_event_bus: None) -> None:
    FeedManager._instance = None  # type: ignore[attr-defined]
    m1: FeedManager = FeedManager()
    m1.add("https://example.com/feed.xml", title="Test Feed")
    FeedManager._instance = None  # type: ignore[attr-defined]
    m2: FeedManager = FeedManager()
    sources = m2.get_all()
    assert len(sources) == 1
    assert sources[0].url == "https://example.com/feed.xml"
    assert sources[0].title == "Test Feed"


def test_refresh_with_mock(
    manager: FeedManager,
    sample_rss_bytes: bytes,
) -> None:
    source = manager.add("https://example.com/feed.xml")
    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        return_value=("Mock Title", [], source.url),
    ):
        new_count: int = manager.refresh(source.id)
    assert new_count == 0
    refreshed = manager.get(source.id)
    assert refreshed.title == "Mock Title"


def test_refresh_returns_new_items_count(
    manager: FeedManager,
    sample_rss_bytes: bytes,
) -> None:
    from core.feed_parser import parse_feed_bytes

    source = manager.add("https://example.com/feed.xml")
    _, items = parse_feed_bytes(sample_rss_bytes, source.id, source.url)
    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        return_value=("Title", items, source.url),
    ):
        new_count: int = manager.refresh(source.id)
    assert new_count == 2
    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        return_value=("Title", items, source.url),
    ):
        new_count = manager.refresh(source.id)
    assert new_count == 0


def test_mark_read(manager: FeedManager, sample_rss_bytes: bytes) -> None:
    from core.feed_parser import parse_feed_bytes

    source = manager.add("https://example.com/feed.xml")
    _, items = parse_feed_bytes(sample_rss_bytes, source.id, source.url)
    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        return_value=("Title", items, source.url),
    ):
        manager.refresh(source.id)
    item_id: str = items[0].id
    manager.mark_read(source.id, item_id)
    refreshed = manager.get(source.id)
    matched = [it for it in refreshed.items if it.id == item_id]
    assert matched and matched[0].read is True


def test_refresh_all_with_empty(manager: FeedManager) -> None:
    result = manager.refresh_all()
    assert result["success"] == 0
    assert result["failed"] == 0


def test_refresh_all_progress_counts_completed_feeds(manager: FeedManager) -> None:
    first = manager.add("https://example.com/one.xml")
    second = manager.add("https://example.com/two.xml")
    progress: list[tuple[str, int, int]] = []

    with patch.object(
        manager,
        "refresh",
        side_effect=[0, FeedError("boom")],
    ):
        result = manager.refresh_all(
            lambda source_id, completed, total: progress.append(
                (source_id, completed, total)
            )
        )

    assert progress == [
        (first.id, 1, 2),
        (second.id, 2, 2),
    ]
    assert result["success"] == 1
    assert result["failed"] == 1
