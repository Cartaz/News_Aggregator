"""Behavioral regressions discovered during the September 2026 audit."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from config.exceptions import ConfigValidationError
from config.settings import SettingsManager
from core.feed_manager import FeedManager
from core.feed_parser import parse_feed_bytes
from core.app_controller import AppController
from core.models import FeedItem, FeedSource


@pytest.mark.parametrize("changes", [
    {"notify_new_items": "false"}, {"window_width": "1280"},
    {"window_height": -1}, {"source_split_width": None},
    {"refresh_interval_minutes": True}, {"refresh_interval_minutes": float("inf")},
    {"font_scale_factor": "1.0"}, {"close_to_tray": []},
    {"max_items_per_feed": 3.5},
    {"refresh_interval_minutes": 10**30},
    {"window_width": 10**30}, {"window_height": 10**30},
    {"font_scale_factor": 10**1000},
])
def test_invalid_settings_never_enter_canonical_state(tmp_paths, changes):
    manager = SettingsManager()
    before = manager.snapshot()
    with pytest.raises(ConfigValidationError):
        manager.update(changes)
    assert manager.snapshot() == before


@pytest.mark.parametrize("filename", ["settings.json", "feeds.json"])
def test_invalid_utf8_does_not_crash_startup(tmp_paths, filename):
    path = tmp_paths / filename
    path.write_bytes(b"\xff\xfe")
    if filename == "settings.json":
        assert SettingsManager(path).settings.window_width == 1280
    else:
        assert FeedManager(path).get_all() == []


def test_bad_items_do_not_discard_valid_source_and_naive_dates_become_utc(tmp_paths):
    path = tmp_paths / "feeds.json"
    valid = {"id": "legacy", "source_id": "old", "title": "Good",
             "published": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
             "read": True}
    path.write_text(json.dumps({"sources": [None, {"url": 123}, {
        "url": "https://example.com/feed.xml", "items": [None, {"published": []}, valid]
    }]}))
    manager = FeedManager(path)
    assert len(manager.get_all()) == 1
    source = manager.get_all()[0]
    assert len(source.items) == 1
    assert source.items[0].published.tzinfo == timezone.utc
    assert source.items[0].source_id == source.id
    assert source.items[0].read is True
    assert len(manager.get_all_items()) == 1
    manager.mark_read(source.id, "legacy")


@pytest.mark.parametrize("xml", [
    b'<rss version="2.0"><channel><title>Empty</title><link>https://example.com</link><description>Empty</description></channel></rss>',
    b'<feed xmlns="http://www.w3.org/2005/Atom"><title>Empty</title><id>urn:empty</id><updated>2026-09-29T00:00:00Z</updated></feed>',
])
def test_valid_empty_feed_is_successful(xml):
    assert parse_feed_bytes(xml, "source", "https://example.com/feed.xml") == ("Empty", [])


def test_saved_item_limit_is_applied_and_latest_articles_win(tmp_paths, monkeypatch):
    manager = FeedManager()
    settings = SettingsManager()
    settings.set("max_items_per_feed", 65)
    controller = AppController(manager, settings)
    source = manager.add("https://example.com/feed.xml")
    now = datetime.now(timezone.utc)
    entries = [FeedItem.from_raw(source.id, str(i), f"https://example.com/{i}", "", now - timedelta(minutes=i)) for i in range(80)]
    monkeypatch.setattr("core.feed_manager.fetch_and_parse_resolved", lambda *a, **k: ("Feed", list(reversed(entries)), source.url))
    try:
        assert manager.refresh(source.id) == 65
        assert manager.get(source.id).items == entries[:65]
        controller.update_settings({"max_items_per_feed": 2})
        manager.refresh(source.id)
        assert manager.get(source.id).items == entries[:2]
    finally:
        controller.shutdown()


def test_unread_badge_excludes_expired_articles():
    source = FeedSource("https://example.com")
    source.items = [FeedItem.from_raw(source.id, "Old", "https://example.com/old", "", datetime.now(timezone.utc) - timedelta(days=3))]
    assert source.unread_count == 0


def test_parser_can_supply_more_than_default_fifty_articles():
    items = ''.join(f'<item><title>{i}</title><guid>urn:item:{i}</guid></item>' for i in range(70))
    _, parsed = parse_feed_bytes(f'<rss version="2.0"><channel><title>Many</title>{items}</channel></rss>'.encode(), "source", "https://example.com/feed.xml")
    assert len(parsed) == 70


def test_cancelled_auto_timer_cannot_reschedule_or_refresh(tmp_paths, monkeypatch):
    controller = AppController()
    calls = []
    monkeypatch.setattr(controller, "refresh_all_async", lambda: calls.append(True))
    try:
        controller.start_auto_refresh()
        generation = controller._auto_generation
        controller.stop_auto_refresh()
        controller._on_auto_refresh(generation)
        assert calls == []
        assert controller._auto_timer is None
    finally:
        controller.shutdown()
