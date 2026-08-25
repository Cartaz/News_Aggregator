"""Regression tests per ETag / Last-Modified e HTTP 304."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from core.exceptions import FeedFetchError
from core.feed_fetcher import FeedFetchResult, fetch_and_parse_resolved
from core.feed_http import HttpFetchResult, fetch_url_response
from core.feed_manager import FeedManager
from core.models import FeedItem


@pytest.fixture
def manager(tmp_paths: Path, reset_event_bus: None) -> FeedManager:
    return FeedManager()


def _item(source_id: str) -> FeedItem:
    return FeedItem.from_raw(
        source_id=source_id,
        title="Article",
        link="https://example.com/article",
        summary="Text",
        published=datetime.now(timezone.utc),
    )


def _seed_http_cache(
    manager: FeedManager,
    source_id: str,
    *,
    resolved_url: str = "",
    etag: str = "",
    last_modified: str = "",
) -> None:
    """Test-only setup for cache metadata owned by FeedManager."""
    with manager._lock:
        source = manager._sources[source_id]
        source.resolved_feed_url = resolved_url
        source.http_etag = etag
        source.http_last_modified = last_modified
    manager.save()


def test_fetch_url_response_sends_validators_and_accepts_304() -> None:
    last_modified = "Fri, 21 Aug 2026 09:00:00 GMT"
    response = MagicMock(
        status_code=304,
        headers={"ETag": '"v1"', "Last-Modified": last_modified},
        content=b"",
    )

    with patch("core.feed_http.requests.get", return_value=response) as get_mock:
        result = fetch_url_response(
            "https://example.com/feed.xml",
            etag='"v1"',
            last_modified=last_modified,
        )

    headers = get_mock.call_args.kwargs["headers"]
    assert headers["If-None-Match"] == '"v1"'
    assert headers["If-Modified-Since"] == last_modified
    assert result.not_modified is True
    assert result.content == b""
    assert result.etag == '"v1"'
    assert result.last_modified == last_modified


def test_fetcher_skips_parser_on_304() -> None:
    with (
        patch(
            "core.feed_fetcher.fetch_url_response",
            return_value=HttpFetchResult(
                b"",
                etag='"same"',
                last_modified="Fri, 21 Aug 2026 09:00:00 GMT",
                not_modified=True,
            ),
        ),
        patch("core.feed_fetcher.parse_feed_bytes") as parse_mock,
    ):
        result = fetch_and_parse_resolved(
            "https://example.com/feed.xml",
            "source-id",
            etag='"same"',
        )

    assert result.not_modified is True
    assert result.items == []
    parse_mock.assert_not_called()


def test_manager_persists_validators_and_preserves_items_on_304(
    manager: FeedManager,
) -> None:
    source = manager.add("https://example.com/feed.xml")
    item = _item(source.id)
    last_modified = "Fri, 21 Aug 2026 09:00:00 GMT"

    first = FeedFetchResult(
        "Example",
        [item],
        source.url,
        etag='"v1"',
        last_modified=last_modified,
    )
    unchanged = FeedFetchResult(
        "",
        [],
        source.url,
        etag='"v1"',
        last_modified=last_modified,
        not_modified=True,
    )

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=[first, unchanged],
    ) as fetch_mock:
        assert manager.refresh(source.id) == 1
        manager.mark_read(source.id, item.id)
        assert manager.refresh(source.id) == 0

    assert fetch_mock.call_args_list == [
        call(source.url, source.id),
        call(
            source.url,
            source.id,
            etag='"v1"',
            last_modified=last_modified,
        ),
    ]
    current = manager.get(source.id)
    assert len(current.items) == 1
    assert current.items[0].read is True
    assert current.http_etag == '"v1"'
    assert current.http_last_modified == last_modified

    reloaded = FeedManager()
    persisted = reloaded.get(source.id)
    assert persisted.http_etag == '"v1"'
    assert persisted.http_last_modified == last_modified
    assert persisted.items[0].read is True


def test_conditional_failure_retries_same_cached_url_without_validators(
    manager: FeedManager,
) -> None:
    source = manager.add("https://example.com")
    cached = "https://example.com/feed.xml"
    _seed_http_cache(manager, source.id, resolved_url=cached, etag='"old"')

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=[
            FeedFetchError(cached, "conditional rejected"),
            FeedFetchResult("Example", [], cached, etag='"new"'),
        ],
    ) as fetch_mock:
        manager.refresh(source.id)

    assert fetch_mock.call_args_list == [
        call(cached, source.id, etag='"old"'),
        call(cached, source.id),
    ]
    current = manager.get(source.id)
    assert current.resolved_feed_url == cached
    assert current.http_etag == '"new"'


def test_new_resolved_url_replaces_old_validators(manager: FeedManager) -> None:
    source = manager.add("https://example.com")
    old_cached = "https://example.com/old.xml"
    new_cached = "https://example.com/new.xml"
    old_last_modified = "Thu, 20 Aug 2026 09:00:00 GMT"
    _seed_http_cache(
        manager,
        source.id,
        resolved_url=old_cached,
        etag='"old"',
        last_modified=old_last_modified,
    )

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=[
            FeedFetchError(old_cached, "conditional failed"),
            FeedFetchError(old_cached, "gone"),
            FeedFetchResult(
                "Example",
                [],
                new_cached,
                etag='"new"',
                last_modified="Fri, 21 Aug 2026 09:00:00 GMT",
            ),
        ],
    ) as fetch_mock:
        manager.refresh(source.id)

    assert fetch_mock.call_args_list == [
        call(
            old_cached,
            source.id,
            etag='"old"',
            last_modified=old_last_modified,
        ),
        call(old_cached, source.id),
        call(source.url, source.id),
    ]
    current = manager.get(source.id)
    assert current.resolved_feed_url == new_cached
    assert current.http_etag == '"new"'
    assert current.http_last_modified == "Fri, 21 Aug 2026 09:00:00 GMT"


def test_200_without_validators_clears_stale_values(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml")
    _seed_http_cache(
        manager,
        source.id,
        etag='"old"',
        last_modified="Thu, 20 Aug 2026 09:00:00 GMT",
    )

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        return_value=FeedFetchResult("Example", [], source.url),
    ):
        manager.refresh(source.id)

    current = manager.get(source.id)
    assert current.http_etag == ""
    assert current.http_last_modified == ""
