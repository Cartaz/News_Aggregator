"""Transactional feed-mutation regression tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.exceptions import FeedError
from core.feed_manager import FeedManager


@pytest.fixture
def manager(tmp_paths: Path) -> FeedManager:
    return FeedManager()


def test_update_feed_persists_title_and_category_once(manager: FeedManager) -> None:
    source = manager.add("https://example.com/feed.xml", title="Before")

    with patch.object(
        manager,
        "_persist_catalog",
        wraps=manager._persist_catalog,
    ) as persist:
        updated = manager.update_feed(source.id, "After", "Tech")

    assert persist.call_count == 1
    assert updated.title == "After"
    assert updated.category == "Tech"

    reloaded = FeedManager()
    persisted = reloaded.get(source.id)
    assert persisted.title == "After"
    assert persisted.category == "Tech"


def test_update_feed_keeps_canonical_state_when_persistence_fails(
    manager: FeedManager,
) -> None:
    source = manager.add("https://example.com/feed.xml", title="Before")
    manager.set_category(source.id, "Old")

    with patch.object(
        manager,
        "_persist_catalog",
        side_effect=FeedError("disk failure"),
    ):
        with pytest.raises(FeedError, match="disk failure"):
            manager.update_feed(source.id, "After", "New")

    current = manager.get(source.id)
    assert current.title == "Before"
    assert current.category == "Old"
