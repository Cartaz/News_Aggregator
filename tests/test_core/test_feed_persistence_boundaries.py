"""Feed ownership and persistence rollback regression tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.exceptions import FeedError
from core.feed_manager import FeedManager


def test_feed_queries_return_detached_snapshots(tmp_paths: Path) -> None:
    manager = FeedManager()
    added = manager.add("https://example.com/feed.xml", "Canonical")

    added.title = "External mutation"
    listed = manager.get_all()
    listed[0].title = "Another external mutation"

    assert manager.get(added.id).title == "Canonical"


def test_refresh_rolls_back_memory_when_atomic_persistence_fails(
    tmp_paths: Path,
) -> None:
    manager = FeedManager()
    source = manager.add("https://example.com/feed.xml", "Canonical")

    with (
        patch(
            "core.feed_manager.fetch_and_parse_resolved",
            return_value=("Changed by refresh", [], source.url),
        ),
        patch("pathlib.Path.replace", side_effect=OSError("disk full")),
        pytest.raises(FeedError),
    ):
        manager.refresh(source.id)

    current = manager.get(source.id)
    assert current.title == "Canonical"
    assert current.items == []
