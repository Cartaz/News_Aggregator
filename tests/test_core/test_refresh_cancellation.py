"""Cancellation and stale-refresh regression coverage."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from core.exceptions import (
    FeedNotFoundError,
    RefreshCancelledError,
)
from core.feed_fetcher import FeedFetchResult
from core.feed_http import fetch_url_response
from core.feed_manager import FeedManager
from core.models import FeedItem


@pytest.fixture
def manager(tmp_paths: Path) -> FeedManager:
    return FeedManager()


def test_removed_and_readded_feed_rejects_stale_refresh_commit(
    manager: FeedManager,
) -> None:
    source = manager.add("https://example.com/feed.xml", title="Original")
    started = threading.Event()
    release = threading.Event()
    events: list[str] = []
    manager.set_event_sink(lambda name, payload: events.append(name))

    stale_item = FeedItem.from_raw(
        source_id=source.id,
        title="Stale result",
        link="https://example.com/stale",
        summary="",
        published=datetime.now(timezone.utc),
    )

    def controlled_fetch(*args, **kwargs):  # type: ignore[no-untyped-def]
        started.set()
        assert release.wait(timeout=2.0)
        return FeedFetchResult("Fetched title", [stale_item], source.url)

    error: list[BaseException] = []

    def run_refresh() -> None:
        try:
            manager.refresh(source.id)
        except BaseException as exc:  # test captures the worker outcome
            error.append(exc)

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=controlled_fetch,
    ):
        worker = threading.Thread(target=run_refresh)
        worker.start()
        assert started.wait(timeout=1.0)

        manager.remove(source.id)
        replacement = manager.add(source.url, title="Replacement")
        assert replacement.id == source.id

        release.set()
        worker.join(timeout=2.0)

    assert not worker.is_alive()
    assert len(error) == 1
    assert isinstance(error[0], RefreshCancelledError)

    current = manager.get(source.id)
    assert current.title == "Replacement"
    assert current.items == []
    assert "feed_refresh_cancelled" in events
    assert "feed_refresh_completed" not in events
    assert "new_items_available" not in events


def test_refresh_all_reports_pre_cancelled_sources_without_network(
    manager: FeedManager,
) -> None:
    for index in range(3):
        manager.add(f"https://example.com/{index}.xml")

    cancel_event = threading.Event()
    cancel_event.set()
    result = manager.refresh_all(cancel_event=cancel_event)

    assert result == {
        "success": 0,
        "failed": 0,
        "errors": [],
        "cancelled": 3,
    }


def test_http_cancellation_stops_before_curl_fallback() -> None:
    cancel_event = threading.Event()

    def fail_and_cancel(*args, **kwargs):  # type: ignore[no-untyped-def]
        cancel_event.set()
        raise requests.exceptions.ConnectionError("offline")

    curl_mock = MagicMock()
    with (
        patch("core.feed_http.requests.get", side_effect=fail_and_cancel),
        patch("core.feed_http._HAS_CURL_CFFI", True),
        patch("core.feed_http.cf_requests", curl_mock),
    ):
        with pytest.raises(RefreshCancelledError):
            fetch_url_response(
                "https://example.com/feed.xml",
                cancel_event=cancel_event,
            )

    curl_mock.get.assert_not_called()


def test_removed_feed_is_still_absent_after_stale_worker_finishes(
    manager: FeedManager,
) -> None:
    source = manager.add("https://example.com/feed.xml")
    started = threading.Event()
    release = threading.Event()

    def controlled_fetch(*args, **kwargs):  # type: ignore[no-untyped-def]
        started.set()
        assert release.wait(timeout=2.0)
        return FeedFetchResult("Example", [], source.url)

    with patch(
        "core.feed_manager.fetch_and_parse_resolved",
        side_effect=controlled_fetch,
    ):
        worker = threading.Thread(
            target=lambda: _ignore_cancelled(manager, source.id)
        )
        worker.start()
        assert started.wait(timeout=1.0)
        manager.remove(source.id)
        release.set()
        worker.join(timeout=2.0)

    assert not worker.is_alive()
    with pytest.raises(FeedNotFoundError):
        manager.get(source.id)

    reloaded = FeedManager()
    with pytest.raises(FeedNotFoundError):
        reloaded.get(source.id)


def _ignore_cancelled(manager: FeedManager, source_id: str) -> None:
    try:
        manager.refresh(source_id)
    except RefreshCancelledError:
        pass
