"""Regression test per la cache dell'URL RSS/Atom risolto."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import call, patch

import pytest

from core.exceptions import FeedFetchError
from core.feed_fetcher import fetch_and_parse_resolved
from core.feed_http import HttpFetchResult
from core.feed_manager import FeedManager
from core.feed_serializer import deserialize_source


@pytest.fixture
def manager(tmp_paths: Path, reset_event_bus: None) -> FeedManager:
    return FeedManager()


def test_old_json_without_resolved_url_remains_compatible() -> None:
    source = deserialize_source(
        {
            "url": "https://example.com",
            "title": "Example",
            "items": [],
        }
    )
    assert source.resolved_feed_url == ""
    assert source.http_etag == ""
    assert source.http_last_modified == ""


def test_discovered_url_is_persisted(
    manager: FeedManager,
    tmp_paths: Path,
) -> None:
    source = manager.add("https://example.com")
    resolved = "https://example.com/feed.xml"

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        return_value=("Example", [], resolved),
    ):
        manager.refresh(source.id)

    assert manager.get(source.id).resolved_feed_url == resolved

    reloaded = FeedManager()
    assert reloaded.get(source.id).resolved_feed_url == resolved


def test_cached_url_is_used_before_original(manager: FeedManager) -> None:
    source = manager.add("https://example.com")
    source.resolved_feed_url = "https://example.com/feed.xml"
    manager.save()

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        return_value=("Example", [], source.resolved_feed_url),
    ) as fetch_mock:
        manager.refresh(source.id)

    fetch_mock.assert_called_once_with(source.resolved_feed_url, source.id)


def test_broken_cache_falls_back_to_original_and_replaces_cache(
    manager: FeedManager,
) -> None:
    source = manager.add("https://example.com")
    old_resolved = "https://example.com/old-feed.xml"
    new_resolved = "https://example.com/new-feed.xml"
    source.resolved_feed_url = old_resolved
    manager.save()

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=[
            FeedFetchError(old_resolved, "gone"),
            ("Example", [], new_resolved),
        ],
    ) as fetch_mock:
        manager.refresh(source.id)

    assert fetch_mock.call_args_list == [
        call(old_resolved, source.id),
        call(source.url, source.id),
    ]
    assert manager.get(source.id).resolved_feed_url == new_resolved


def test_fetcher_reports_auto_discovered_feed_url(
    sample_rss_bytes: bytes,
) -> None:
    homepage = b"<html><head></head><body>Example</body></html>"
    original = "https://example.com"
    resolved = "https://example.com/feed.xml"

    with (
        patch(
            "core.feed_fetcher.fetch_url_response",
            side_effect=[
                HttpFetchResult(homepage),
                HttpFetchResult(sample_rss_bytes),
            ],
        ),
        patch(
            "core.feed_fetcher.extract_feed_links",
            return_value=[resolved],
        ),
    ):
        title, items, actual_url = fetch_and_parse_resolved(
            original,
            "source-id",
        )

    assert title == "Feed di Prova"
    assert len(items) == 2
    assert actual_url == resolved
