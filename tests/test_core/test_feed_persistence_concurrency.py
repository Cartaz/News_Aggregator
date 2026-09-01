"""Concurrency regressions for feed persistence and canonical-state publication."""

from __future__ import annotations

import threading
from pathlib import Path

from core.feed_manager import FeedManager
from core.models import FeedSource


def test_feed_reads_do_not_wait_for_catalog_filesystem_io(tmp_paths: Path) -> None:
    manager = FeedManager()
    source = manager.add("https://example.com/feed.xml", title="Before")
    started = threading.Event()
    release = threading.Event()
    original_persist = manager._persist_catalog

    def delayed_persist(catalog: dict[str, FeedSource]) -> None:
        started.set()
        assert release.wait(timeout=2.0)
        original_persist(catalog)

    manager._persist_catalog = delayed_persist  # type: ignore[method-assign]
    writer = threading.Thread(
        target=lambda: manager.update_feed(source.id, "After", "Tech"),
        name="feed-persistence-test",
    )
    writer.start()
    assert started.wait(timeout=1.0)

    read_done = threading.Event()
    observed: dict[str, str] = {}

    def read_current() -> None:
        observed["title"] = manager.get(source.id).title
        read_done.set()

    reader = threading.Thread(target=read_current, name="feed-reader-test")
    reader.start()

    assert read_done.wait(timeout=0.5)
    assert observed["title"] == "Before"

    release.set()
    writer.join(timeout=1.0)
    reader.join(timeout=1.0)
    assert writer.is_alive() is False
    assert manager.get(source.id).title == "After"


def test_catalog_io_is_serialized_without_holding_the_state_lock(
    tmp_paths: Path,
) -> None:
    manager = FeedManager()
    first = manager.add("https://example.com/one.xml", title="One")
    second = manager.add("https://example.com/two.xml", title="Two")

    barrier = threading.Barrier(2)
    failures: list[BaseException] = []

    def update(source_id: str, title: str) -> None:
        try:
            barrier.wait(timeout=1.0)
            manager.update_feed(source_id, title, "Tech")
        except BaseException as exc:  # pragma: no cover - diagnostic capture
            failures.append(exc)

    one = threading.Thread(target=update, args=(first.id, "One Updated"))
    two = threading.Thread(target=update, args=(second.id, "Two Updated"))
    one.start()
    two.start()
    one.join(timeout=2.0)
    two.join(timeout=2.0)

    assert failures == []
    assert one.is_alive() is False
    assert two.is_alive() is False
    assert manager.get(first.id).title == "One Updated"
    assert manager.get(second.id).title == "Two Updated"

    reloaded = FeedManager()
    assert reloaded.get(first.id).title == "One Updated"
    assert reloaded.get(second.id).title == "Two Updated"
