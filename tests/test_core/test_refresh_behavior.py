"""Refresh behaviour: dates, persistence cost, notifications and startup."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from config.settings import SettingsManager
from core.app_controller import AppController
from core.feed_fetcher import FeedFetchResult
from core.feed_manager import FeedManager
from core.feed_parser import parse_feed_bytes

UNDATED_RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
<item><title>Senza data</title><link>https://example.com/undated</link></item>
</channel></rss>"""


@pytest.fixture
def manager(tmp_paths: Path) -> FeedManager:
    return FeedManager(tmp_paths / "feeds.json")


def _undated_result(source_id: str, url: str) -> FeedFetchResult:
    title, items = parse_feed_bytes(UNDATED_RSS, source_id, url)
    return FeedFetchResult(title, items, url)


def test_undated_item_keeps_first_seen_date_across_refreshes(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml")
    title, items = parse_feed_bytes(UNDATED_RSS, source.id, source.url)
    # The parser stamps undated entries with "now": a later fetch sees a later date.
    later = [replace(item, published=item.published + timedelta(hours=3)) for item in items]
    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=[
            FeedFetchResult(title, items, source.url),
            FeedFetchResult(title, later, source.url),
        ],
    ):
        manager.refresh(source.id)
        assert manager.refresh(source.id) == 0

    assert manager.get(source.id).items[0].published == items[0].published


def test_corrected_earlier_date_is_accepted(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml")
    title, items = parse_feed_bytes(UNDATED_RSS, source.id, source.url)
    earlier = [replace(item, published=item.published - timedelta(hours=1)) for item in items]
    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=[
            FeedFetchResult(title, items, source.url),
            FeedFetchResult(title, earlier, source.url),
        ],
    ):
        manager.refresh(source.id)
        manager.refresh(source.id)

    assert manager.get(source.id).items[0].published == earlier[0].published


def test_unchanged_304_does_not_rewrite_the_catalog(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml")
    not_modified = FeedFetchResult("", [], source.url, etag='"v1"', not_modified=True)
    with patch("core.feed_manager.fetch_and_parse_resolved", return_value=not_modified):
        manager.refresh(source.id)  # validators change from empty to "v1": dirty
        manager.flush()
        with patch.object(manager, "_persist_catalog", wraps=manager._persist_catalog) as persist:
            manager.refresh(source.id)
            manager.refresh(source.id)

    assert persist.call_count == 0
    assert manager.get(source.id).last_updated is not None
    assert FeedManager(manager._path).get(source.id).http_etag == '"v1"'


def test_first_fetch_is_not_announced_as_new_items(manager: FeedManager) -> None:
    events: list[str] = []
    manager.set_event_sink(lambda name, _payload: events.append(name))
    source = manager.add("https://example.com/feed.xml")
    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=lambda url, sid, **_: _undated_result(sid, url),
    ):
        assert manager.refresh(source.id) == 1

    assert "feed_refresh_completed" in events
    assert "new_items_available" not in events


def test_new_items_after_first_fetch_are_announced(manager: FeedManager, sample_rss_bytes: bytes) -> None:
    events: list[str] = []
    manager.set_event_sink(lambda name, _payload: events.append(name))
    source = manager.add("https://example.com/feed.xml")
    title, items = parse_feed_bytes(sample_rss_bytes, source.id, source.url)
    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=[
            FeedFetchResult(title, items[:1], source.url),
            FeedFetchResult(title, items, source.url),
        ],
    ):
        manager.refresh(source.id)
        assert manager.refresh(source.id) == 1

    assert events.count("new_items_available") == 1


def test_start_refreshes_immediately_and_schedules_the_next_cycle(tmp_paths: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    controller = AppController(
        FeedManager(tmp_paths / "feeds.json"),
        SettingsManager(tmp_paths / "settings.json"),
    )
    calls: list[bool] = []
    monkeypatch.setattr(controller, "refresh_all_async", lambda: calls.append(True) or True)
    try:
        controller.start()
        assert calls == [True]
        assert controller._auto_timer is not None
        assert controller._auto_timer.interval == 15 * 60
    finally:
        controller.shutdown()
