"""Feed ownership and the two persistence speeds (transactional vs deferred)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from core.exceptions import FeedError
from core.feed_fetcher import FeedFetchResult
from core.feed_manager import FeedManager


def test_feed_queries_return_detached_snapshots(tmp_paths: Path) -> None:
    manager = FeedManager()
    added = manager.add("https://example.com/feed.xml", "Canonical")

    added.title = "External mutation"
    listed = manager.get_all()
    listed[0].title = "Another external mutation"

    assert manager.get(added.id).title == "Canonical"


def test_failed_flush_keeps_refresh_pending_and_retries(tmp_paths: Path) -> None:
    manager = FeedManager()
    source = manager.add("https://example.com/feed.xml", "Canonical")

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        return_value=FeedFetchResult("Changed by refresh", [], source.url, etag='"v2"'),
    ):
        manager.refresh(source.id)

    with patch("pathlib.Path.replace", side_effect=OSError("disk full")):
        with pytest.raises(FeedError):
            manager.flush()
    assert manager.has_pending_changes

    manager.flush()
    assert not manager.has_pending_changes
    assert FeedManager().get(source.id).http_etag == '"v2"'


def test_refresh_does_not_write_until_flush(tmp_paths: Path) -> None:
    manager = FeedManager(flush_delay=60)
    source = manager.add("https://example.com/feed.xml", "Canonical")

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        return_value=FeedFetchResult("Title", [], source.url, etag='"v2"'),
    ):
        manager.refresh(source.id)

    assert FeedManager().get(source.id).http_etag == ""
    manager.close()
    assert FeedManager().get(source.id).http_etag == '"v2"'


def test_refresh_all_writes_the_catalog_once(tmp_paths: Path) -> None:
    manager = FeedManager(flush_delay=60)
    sources = [manager.add(f"https://example.com/{index}.xml") for index in range(5)]

    with (
        patch(
            "core.feed_manager.fetch_and_parse_resolved",
            side_effect=lambda url, sid, **_: FeedFetchResult("T", [], url, etag='"x"'),
        ),
        patch.object(manager, "_persist_catalog", wraps=manager._persist_catalog) as persist,
    ):
        result = manager.refresh_all()

    assert result["success"] == len(sources)
    assert persist.call_count == 1


def test_mark_read_is_flushed_after_the_debounce(tmp_paths: Path, sample_rss_bytes: bytes) -> None:
    from core.feed_parser import parse_feed_bytes

    manager = FeedManager(flush_delay=0.05)
    source = manager.add("https://example.com/feed.xml")
    title, items = parse_feed_bytes(sample_rss_bytes, source.id, source.url)
    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        return_value=FeedFetchResult(title, items, source.url),
    ):
        manager.refresh(source.id)
    manager.flush()

    manager.mark_read(source.id, items[0].id)
    deadline = time.monotonic() + 2.0
    while manager.has_pending_changes and time.monotonic() < deadline:
        time.sleep(0.01)

    assert not manager.has_pending_changes
    reloaded = {item.id: item.read for item in FeedManager().get(source.id).items}
    assert reloaded[items[0].id] is True
