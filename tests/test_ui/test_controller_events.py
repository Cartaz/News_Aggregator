"""How the QML adapter reacts to controller events, without a window."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtQuick")

from config.constants import Paths
from config.settings import SettingsManager
from core.app_controller import AppController
from core.feed_manager import FeedManager
from ui.controller import UiController


class _NoopSiteIcons:
    def cached_icon_for(self, _source):  # type: ignore[no-untyped-def]
        return None

    def request_icon(self, _source, _callback) -> None:  # type: ignore[no-untyped-def]
        return None

    def shutdown(self) -> None:
        return None


@pytest.fixture
def backend(tmp_paths, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr("ui.controller.SiteIconService", _NoopSiteIcons)
    manager = FeedManager(Paths.FEEDS_FILE)
    controller = AppController(manager, SettingsManager(Paths.SETTINGS_FILE))
    ui = UiController(controller)
    yield manager, controller, ui
    ui.shutdown()
    controller.shutdown()


def test_background_feed_failure_updates_status_without_toast(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, _controller, ui = backend
    source = manager.add("https://example.com/feed.xml", title="Broken")
    toasts: list[str] = []
    ui.toastRequested.connect(lambda title, _message, _error: toasts.append(title))

    manager._emit_event("feed_refresh_failed", {"source_id": source.id, "error": "down"})
    qtbot.wait(50)

    assert toasts == []


def test_navigation_mark_read_updates_rows_without_resetting_the_list(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    from datetime import datetime, timedelta, timezone

    from core.models import FeedItem

    manager, _controller, ui = backend
    source = manager.add("https://example.com/feed.xml", title="Feed")
    items = [
        FeedItem.from_raw(
            source.id,
            f"Item {index}",
            f"https://example.com/{index}",
            "Summary",
            datetime.now(timezone.utc) - timedelta(minutes=index),
        )
        for index in range(5)
    ]
    with manager._lock:
        manager._sources[source.id].items = items
    ui.sync()
    resets: list[bool] = []
    ui.articles.modelReset.connect(lambda: resets.append(True))

    ui.selectArticle(1)
    ui.selectArticle(2)  # leaving item 1 marks it read
    qtbot.waitUntil(lambda: ui.articles.row(1).item.read, timeout=2000)

    assert resets == []
    assert manager.get(source.id).items[1].read is True
