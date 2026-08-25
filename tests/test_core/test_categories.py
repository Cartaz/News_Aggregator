"""Test per le nuove funzionalità: rename, category, mega-feed."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.exceptions import FeedError, FeedNotFoundError
from core.feed_manager import FeedManager


@pytest.fixture
def manager(tmp_paths: Path) -> FeedManager:
    FeedManager._instance = None  # type: ignore[attr-defined]
    return FeedManager()


def test_rename_feed(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml", title="Originale")
    renamed = manager.rename_feed(source.id, "Nuovo Nome")
    assert renamed.title == "Nuovo Nome"
    assert manager.get(source.id).title == "Nuovo Nome"


def test_rename_feed_empty_raises(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml")
    with pytest.raises(FeedError):
        manager.rename_feed(source.id, "   ")


def test_rename_feed_unknown_raises(manager: FeedManager) -> None:
    with pytest.raises(FeedNotFoundError):
        manager.rename_feed("nonexistent", "Nome")


def test_set_category(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml")
    updated = manager.set_category(source.id, "Tech")
    assert updated.category == "Tech"
    assert manager.get(source.id).category == "Tech"


def test_set_category_empty_removes(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml")
    manager.set_category(source.id, "Tech")
    manager.set_category(source.id, "")
    assert manager.get(source.id).category == ""


def test_get_categories(manager: FeedManager) -> None:
    s1 = manager.add("https://a.com/feed")
    s2 = manager.add("https://b.com/feed")
    s3 = manager.add("https://c.com/feed")
    manager.set_category(s1.id, "Games")
    manager.set_category(s2.id, "Tech")
    manager.set_category(s3.id, "Tech")
    cats = manager.get_categories()
    assert cats == ["Games", "Tech"]


def test_get_feeds_by_category(manager: FeedManager) -> None:
    s1 = manager.add("https://a.com/feed")
    s2 = manager.add("https://b.com/feed")
    manager.set_category(s1.id, "Tech")
    manager.set_category(s2.id, "Games")
    tech_feeds = manager.get_feeds_by_category("Tech")
    assert len(tech_feeds) == 1
    assert tech_feeds[0].url == "https://a.com/feed"


def test_get_items_by_category(manager: FeedManager, sample_rss_bytes: bytes) -> None:
    from core.feed_parser import parse_feed_bytes

    s1 = manager.add("https://a.com/feed")
    s2 = manager.add("https://b.com/feed")
    manager.set_category(s1.id, "Tech")
    manager.set_category(s2.id, "Tech")

    _, items_a = parse_feed_bytes(sample_rss_bytes, s1.id, s1.url)
    _, items_b = parse_feed_bytes(sample_rss_bytes, s2.id, s2.url)

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=[
            ("Feed A", items_a, s1.url),
            ("Feed B", items_b, s2.url),
        ],
    ):
        manager.refresh(s1.id)
        manager.refresh(s2.id)

    tech_items = manager.get_items_by_category("Tech")
    assert len(tech_items) == 4
    for i in range(len(tech_items) - 1):
        assert tech_items[i].published >= tech_items[i + 1].published


def test_get_all_items_mega_feed(manager: FeedManager, sample_rss_bytes: bytes) -> None:
    from core.feed_parser import parse_feed_bytes

    s1 = manager.add("https://a.com/feed")
    s2 = manager.add("https://b.com/feed")

    _, items_a = parse_feed_bytes(sample_rss_bytes, s1.id, s1.url)
    _, items_b = parse_feed_bytes(sample_rss_bytes, s2.id, s2.url)

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=[
            ("Feed A", items_a, s1.url),
            ("Feed B", items_b, s2.url),
        ],
    ):
        manager.refresh(s1.id)
        manager.refresh(s2.id)

    all_items = manager.get_all_items()
    assert len(all_items) == 4
    for i in range(len(all_items) - 1):
        assert all_items[i].published >= all_items[i + 1].published


def test_category_persistence(tmp_paths: Path) -> None:
    FeedManager._instance = None  # type: ignore[attr-defined]
    m1 = FeedManager()
    source = m1.add("https://example.com/feed", title="Originale")
    m1.set_category(source.id, "Tech")
    m1.rename_feed(source.id, "Rinominato")
    FeedManager._instance = None  # type: ignore[attr-defined]
    m2 = FeedManager()
    sources = m2.get_all()
    assert len(sources) == 1
    assert sources[0].title == "Rinominato"
    assert sources[0].category == "Tech"
